from common.logger import get_logger
from registry.domain.models.group import Group
from registry.domain.models.organization import Organization

logger = get_logger(__name__)


class OrganizationFactory:

    @staticmethod
    def parse_raw_organization(payload):
        org_id = payload.get("org_id", None)
        org_name = payload.get("org_name", None)
        org_type = payload.get("org_type", None)
        org_uuid = payload.get("org_uuid", None)
        description = payload.get("description", None)
        short_description = payload.get("short_description", None)
        url = payload.get("url", None)
        contacts = payload.get("contacts", None)
        assets = payload.get("assets", None)
        metadata_ipfs_hash = payload.get("metadata_ipfs_hash", None)
        groups = OrganizationFactory.parse_raw_list_groups(payload.get("groups", []))
        organization = Organization(org_name, org_id, org_uuid, org_type, description,
                                    short_description, url, contacts, assets, metadata_ipfs_hash)
        organization.add_all_groups(groups)
        return organization

    @staticmethod
    def parse_raw_list_groups(raw_groups):
        groups = []
        for group in raw_groups:
            groups.append(OrganizationFactory.parse_raw_group(group))
        return groups

    @staticmethod
    def parse_raw_group(raw_group):
        group_id = raw_group.get("id", None)
        group_name = raw_group.get("name", None)
        payment_address = raw_group.get("payment_address", None)
        payment_config = raw_group.get("payment_config", None)
        group = Group(group_name, group_id, payment_address, payment_config)
        return group

    @staticmethod
    def parse_organization_data_model(item):
        organization = Organization(
            item.name, item.org_id, item.org_uuid, item.type, item.description,
            item.short_description, item.url, item.contacts, item.assets, item.metadata_ipfs_hash
        )
        return organization

    @staticmethod
    def parse_organization_data_model_list(items):
        organizations = []
        for item in items:
            organizations.append(OrganizationFactory.parse_organization_data_model(item))
        return organizations

    @staticmethod
    def parse_organization_workflow_data_model_list(items):
        organizations = []
        for item in items:
            organizations.append(OrganizationFactory.parse_organization_data_model(item.Organization))
        return organizations