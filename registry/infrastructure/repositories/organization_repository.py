from datetime import datetime

from sqlalchemy import desc, func, or_

from registry.constants import OrganizationStatus
from registry.domain.factory.organization_factory import OrganizationFactory
from registry.infrastructure.models.models import Group, GroupHistory, Organization, OrganizationAddress, \
    OrganizationAddressHistory, OrganizationHistory, OrganizationReviewWorkflow
from registry.infrastructure.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository):

    def draft_update_org(self, organization, username):
        current_drafts = self.get_org_with_status(organization.org_uuid, OrganizationStatus.DRAFT.value)
        if len(current_drafts) > 0:
            self.update_org_draft(current_drafts[0], organization, username)
        else:
            self.add_org_with_status(organization, OrganizationStatus.DRAFT.value, username)

    def add_org_with_status(self, organization, status, username, transaction_hash=None, wallet_address=None):
        current_time = datetime.utcnow()
        groups = organization.groups
        group_data = self.group_data_items_from_group_list(groups, organization.org_uuid)
        address_data = self.address_data_items_from_address_list(addresses=organization.addresses)
        organization_item = Organization(
            name=organization.name, org_uuid=organization.org_uuid, org_id=organization.org_id,
            type=organization.org_type, description=organization.description,
            short_description=organization.short_description, url=organization.url, duns_no=organization.duns_no,
            origin=organization.origin, owner_name=organization.owner_name, contacts=organization.contacts,
            assets=organization.assets, owner=organization.owner, metadata_ipfs_hash=organization.metadata_ipfs_hash,
            groups=group_data, address=address_data
        )
        self.add_item(organization_item)
        org_row_id = organization_item.row_id

        self.add_item(
            OrganizationReviewWorkflow(
                org_row_id=org_row_id, status=status, created_by=username, updated_by=username,
                created_on=current_time, updated_on=current_time, transaction_hash=transaction_hash,
                wallet_address=wallet_address
            )
        )
        self.session.commit()

    def update_org_draft(self, current_draft, organization, username):
        current_draft.Organization.name = organization.name
        current_draft.Organization.org_id = organization.org_id
        current_draft.Organization.type = organization.org_type
        current_draft.Organization.description = organization.description
        current_draft.Organization.short_description = organization.short_description
        current_draft.Organization.url = organization.url
        current_draft.Organization.duns_no = organization.duns_no
        current_draft.Organization.origin = organization.origin
        current_draft.Organization.owner_name = organization.owner_name
        current_draft.Organization.contacts = organization.contacts
        current_draft.Organization.assets = organization.assets
        current_draft.Organization.metadata_ipfs_hash = organization.metadata_ipfs_hash
        current_draft.OrganizationReviewWorkflow.updated_by = username
        current_draft.OrganizationReviewWorkflow.updated_on = datetime.utcnow()
        self.delete_and_insert_organization_address(org_row_id=current_draft.Organization.row_id,
                                                    addresses=organization.addresses)
        self.session.commit()
        self.add_new_draft_groups_in_draft_org(organization.groups, current_draft, username)

    def delete_and_insert_organization_address(self, org_row_id, addresses):
        self.session.query(OrganizationAddress).filter(OrganizationAddress.org_row_id == org_row_id)\
            .delete(synchronize_session='fetch')
        self.add_organization_address(addresses=addresses, org_row_id=org_row_id)

    def approve_org(self, org_uuid, approver):
        org = self.get_latest_org_from_org_uuid(org_uuid)
        if org[0].OrganizationReviewWorkflow.status == OrganizationStatus.APPROVAL_PENDING.value:
            org[0].OrganizationReviewWorkflow.status = OrganizationStatus.APPROVED.value
            org[0].OrganizationReviewWorkflow.approved_by = approver
        self.session.commit()

    def add_organization_address(self, addresses, org_row_id):
        org_addresses = []
        for address in addresses:
            address_data = address.to_dict()
            org_addresses.append(
                OrganizationAddress(
                    org_row_id=org_row_id,
                    address_type=address_data["address_type"],
                    street_address=address_data["street_address"],
                    apartment=address_data["apartment"],
                    city=address_data["city"],
                    pincode=address_data["pincode"],
                    state=address_data["state"],
                    country=address_data["country"],
                    created_on=datetime.utcnow(),
                    updated_on=datetime.utcnow(),
                )
            )
        self.add_all_items(org_addresses)

    def get_organization_draft(self, org_uuid):
        organizations = self.get_org_with_status(org_uuid, OrganizationStatus.DRAFT.value)
        return OrganizationFactory.parse_organization_workflow_data_model_list(organizations)

    def get_approved_org(self, org_uuid):
        organizations = self.get_org_with_status(org_uuid, OrganizationStatus.APPROVED.value)
        return OrganizationFactory.parse_organization_workflow_data_model_list(organizations)

    def get_org_with_status(self, org_uuid, status):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow) \
            .join(OrganizationReviewWorkflow, OrganizationReviewWorkflow.org_row_id == Organization.row_id) \
            .filter(Organization.org_uuid == org_uuid) \
            .filter(OrganizationReviewWorkflow.status == status).all()
        return organizations

    def get_org_for_uuid(self, org_uuid):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow) \
            .join(OrganizationReviewWorkflow, OrganizationReviewWorkflow.org_row_id == Organization.row_id) \
            .filter(Organization.org_uuid == org_uuid).all()
        return organizations

    def move_non_published_org_to_history(self, org_uuid):
        orgs_with_status = self.session.query(Organization) \
            .join(OrganizationReviewWorkflow, Organization.row_id == OrganizationReviewWorkflow.org_row_id) \
            .filter(Organization.org_uuid == org_uuid) \
            .filter(or_(OrganizationReviewWorkflow.status == OrganizationStatus.APPROVAL_PENDING.value,
                        OrganizationReviewWorkflow.status == OrganizationStatus.APPROVED.value)).all()
        self.move_organizations_to_history(orgs_with_status)

    def get_org_status(self, org_uuid):
        organizations = self.get_latest_org_from_org_uuid(org_uuid)
        return OrganizationFactory.parse_organization_details(organizations)

    def move_organizations_to_history(self, organizations):
        if len(organizations) > 0:
            org_history = []
            row_ids = []
            for org in organizations:
                row_ids.append(org.row_id)
                org_addresses_history = self.clone_address_db_model_list(org.address, history=True)
                org_group_history = self.clone_group_db_model_list(org.groups, history=True)
                org_history.append(OrganizationHistory(
                    row_id=org.row_id,
                    name=org.name,
                    org_uuid=org.org_uuid,
                    org_id=org.org_id,
                    type=org.type,
                    description=org.description,
                    short_description=org.short_description,
                    url=org.url,
                    duns_no=org.duns_no,
                    origin=org.origin,
                    owner_name=org.owner_name,
                    contacts=org.contacts,
                    assets=org.assets,
                    owner=org.owner,
                    metadata_ipfs_hash=org.metadata_ipfs_hash,
                    address=org_addresses_history,
                    groups=org_group_history
                ))

            self.add_all_items(org_history)
            self.session.query(Organization).filter(Organization.row_id.in_(row_ids)) \
                .delete(synchronize_session='fetch')
            self.session.commit()

    def move_org_to_history_with_status(self, org_uuid, status):
        orgs_with_status = self.session.query(Organization) \
            .join(OrganizationReviewWorkflow, Organization.row_id == OrganizationReviewWorkflow.org_row_id) \
            .filter(Organization.org_uuid == org_uuid) \
            .filter(OrganizationReviewWorkflow.status == status).all()
        self.move_organizations_to_history(orgs_with_status)

    def get_published_org_for_user(self, username):
        organizations = self.session.query(Organization) \
            .join(OrganizationReviewWorkflow, Organization.row_id == OrganizationReviewWorkflow.org_row_id) \
            .filter(OrganizationReviewWorkflow == OrganizationStatus.PUBLISHED.value) \
            .filter(Organization.owner == username).all()
        return OrganizationFactory.parse_organization_details(organizations)

    def get_latest_organization(self, username):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow, func.row_number().over(
                partition_by=Organization.org_uuid, order_by=OrganizationReviewWorkflow.updated_on).label("rn")
        ).join(OrganizationReviewWorkflow, Organization.row_id == OrganizationReviewWorkflow.org_row_id) \
            .filter(Organization.owner == username).all()
        latest_orgs = []
        for org in organizations:
            if org.rn == 1:
                latest_orgs.append(org)
        return OrganizationFactory.parse_organization_details(latest_orgs)

    def get_published_organization(self):
        organization = self.session.query(Organization) \
            .join(OrganizationReviewWorkflow, Organization.row_id == OrganizationReviewWorkflow.org_row_id) \
            .filter(OrganizationReviewWorkflow == OrganizationStatus.PUBLISHED.value)
        return OrganizationFactory.parse_organization_data_model_list(organization)

    def change_org_status(self, org_uuid, current_status, new_status, username):
        organizations = self.get_org_with_status(org_uuid, current_status)
        if len(organizations) > 0:
            self._update_org_status(organizations[0], new_status, username)
            self.session.commit()
        else:
            raise Exception(f"DRAFT for organization {org_uuid} not found")

    def _update_org_status(self, org_workflow_model, status, username):
        current_utc_time = datetime.utcnow()
        org_workflow_model.OrganizationReviewWorkflow.status = status
        org_workflow_model.OrganizationReviewWorkflow.updated_on = current_utc_time
        org_workflow_model.OrganizationReviewWorkflow.updated_by = username

    def add_group(self, groups, org_uuid, username):
        organizations = self.get_latest_org_from_org_uuid(org_uuid)
        if len(organizations) == 0:
            raise Exception(f"No org data for the org_uuid {org_uuid}")
        org = organizations[0]
        if org.OrganizationReviewWorkflow.status == OrganizationStatus.DRAFT.value:
            self.add_new_draft_groups_in_draft_org(groups, org, username)
        elif org.OrganizationReviewWorkflow.status == OrganizationStatus.APPROVAL_PENDING.value:
            self.add_new_draft_groups_in_draft_org(groups, org, username)
            self.move_org_to_history_with_status(org_uuid, OrganizationStatus.APPROVAL_PENDING.value)
        elif org.OrganizationReviewWorkflow.status == OrganizationStatus.APPROVED.value:
            self.add_new_draft_groups_in_draft_org(groups, org, username)
            self.move_org_to_history_with_status(org_uuid, OrganizationStatus.APPROVED.value)
        else:
            self.add_new_draft_groups_in_org(groups, org, username)

    def get_latest_org_from_org_uuid(self, org_uuid):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow) \
            .join(OrganizationReviewWorkflow, OrganizationReviewWorkflow.org_row_id == Organization.row_id) \
            .filter(Organization.org_uuid == org_uuid) \
            .order_by(desc(OrganizationReviewWorkflow.updated_on)).all()
        if len(organizations) == 0:
            return []
        return [organizations[0]]

    def add_new_draft_groups_in_draft_org(self, groups, organization, username):
        org_row_id = organization.Organization.row_id
        self.session.query(Group).filter(Group.org_row_id == org_row_id).delete()
        self.session.commit()
        groups = [Group(
            org_row_id=org_row_id,
            org_uuid=organization.Organization.org_uuid, id=group.group_id, name=group.name,
            payment_config=group.payment_config, payment_address=group.payment_address, status=""
        ) for group in groups]
        organization.OrganizationReviewWorkflow.updated_on = datetime.utcnow()
        organization.OrganizationReviewWorkflow.updated_by = username
        self.add_all_items(groups)
        self.session.commit()

    def group_data_items_from_group_list(self, groups, org_uuid):
        group_data = []
        for group in groups:
            group_data.append(Group(
                name=group.name, id=group.group_id, org_uuid=org_uuid,
                payment_address=group.payment_address,
                payment_config=group.payment_config, status=""
            ))
        return group_data

    def address_data_items_from_address_list(self, addresses):
        address_data = []
        for address in addresses:
            address_dict = address.to_dict()
            address_data.append(
                OrganizationAddress(
                    address_type=address_dict["address_type"],
                    street_address=address_dict["street_address"],
                    apartment=address_dict["apartment"],
                    city=address_dict["city"],
                    pincode=address_dict["pincode"],
                    state=address_dict["state"],
                    country=address_dict["country"],
                    updated_on=datetime.utcnow(),
                    created_on=datetime.utcnow()
                ))
        return address_data

    def clone_group_db_model_list(self, groups, history):
        group_data = []
        if history:
            for group in groups:
                group_data.append(GroupHistory(
                    name=group.name, id=group.id, org_uuid=group.org_uuid,
                    payment_address=group.payment_address,
                    payment_config=group.payment_config, status=""
                ))
        else:
            for group in groups:
                group_data.append(Group(
                    name=group.name, id=group.id, org_uuid=group.org_uuid,
                    payment_address=group.payment_address,
                    payment_config=group.payment_config, status=""
                ))
        return group_data

    def clone_address_db_model_list(self, addresses, history):
        address_data = []
        current_time = datetime.utcnow()
        if history:
            for address in addresses:
                address_data.append(OrganizationAddressHistory(
                    address_type=address.address_type, street_address=address.address_type, apartment=address.apartment,
                    city=address.city, pincode=address.pincode, state=address.state,
                    country=address.country, created_on=current_time, updated_on=current_time
                ))
        else:
            for address in addresses:
                address_data.append(OrganizationAddress(
                    address_type=address.address_type, street_address=address.address_type, apartment=address.apartment,
                    city=address.city, pincode=address.pincode, state=address.state,
                    country=address.country, created_on=current_time, updated_on=current_time
                ))
        return address_data

    def add_new_draft_groups_in_org(self, groups, organization, username):
        current_time = datetime.utcnow()
        organization = organization.Organization
        group_data = self.group_data_items_from_group_list(groups, organization.org_uuid)
        address_data = self.clone_address_db_model_list(organization.address, history=False)
        organization_item = Organization(
            name=organization.name,
            org_uuid=organization.org_uuid,
            org_id=organization.org_id,
            type=organization.type,
            owner=organization.owner,
            duns_no=organization.duns_no,
            owner_name=organization.owner_name,
            description=organization.description,
            short_description=organization.short_description,
            url=organization.url,
            contacts=organization.contacts,
            assets=organization.assets,
            metadata_ipfs_hash=organization.metadata_ipfs_hash,
            groups=group_data,
            address=address_data
        )
        self.add_item(organization_item)
        org_row_id = organization_item.row_id

        self.add_item(
            OrganizationReviewWorkflow(
                org_row_id=org_row_id,
                status=OrganizationStatus.DRAFT.value,
                created_by=username,
                updated_by=username,
                created_on=current_time,
                updated_on=current_time,
            )
        )
        self.session.commit()

    def persist_metadata_and_assets_ipfs_hash(self, organization):
        org_data = self.get_org_with_status(organization.org_uuid, OrganizationStatus.APPROVED.value)
        if len(org_data) == 0:
            raise Exception(f"No organization found with {organization.org_uuid}")
        org_item = org_data[0]
        org_item.Organization.metadata_ipfs_hash = organization.metadata_ipfs_hash
        org_item.Organization.assets = organization.assets
        self.session.commit()

    def get_org_with_status_using_org_id(self, org_id, status):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow) \
            .join(OrganizationReviewWorkflow, OrganizationReviewWorkflow.org_row_id == Organization.row_id) \
            .filter(Organization.org_id == org_id) \
            .filter(OrganizationReviewWorkflow.status == status).all()
        return OrganizationFactory.parse_organization_details(organizations)

    def get_org_using_org_id(self, org_uuid):
        organizations = self.session.query(Organization, OrganizationReviewWorkflow) \
            .join(OrganizationReviewWorkflow, OrganizationReviewWorkflow.org_row_id == Organization.row_id) \
            .filter(Organization.org_uuid == org_uuid).all()
        return OrganizationFactory.parse_organization_details(organizations)
