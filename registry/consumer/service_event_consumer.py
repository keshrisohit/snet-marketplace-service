import os
from uuid import uuid4

from web3 import Web3

from common import blockchain_util
from common import ipfs_util
from common.logger import get_logger
from registry.config import NETWORK_ID
from registry.constants import DEFAULT_SERVICE_RANKING, ServiceStatus
from registry.domain.factory.service_factory import ServiceFactory
from registry.domain.models.service import Service

logger = get_logger(__name__)
BLOCKCHAIN_USER = "BLOCKCHAIN_USER"


class ServiceEventConsumer(object):

    def __init__(self, ws_provider, ipfs_url, ipfs_port, service_repository, organiztion_repository):
        self._blockchain_util = blockchain_util.BlockChainUtil("WS_PROVIDER", ws_provider)
        self._service_repository = service_repository
        self._organiztion_repository = organiztion_repository
        self._ipfs_util = ipfs_util.IPFSUtil(ipfs_url, ipfs_port)

    def on_event(self, event):
        pass

    def _fetch_tags(self, registry_contract, org_id_hex, service_id_hex):
        tags_data = registry_contract.functions.getServiceRegistrationById(
            org_id_hex, service_id_hex).call()

        str_tag_data = []
        for tag in tags_data[3]:
            str_tag_data.append(tag.decode())
        return str_tag_data

    def _get_org_id_from_event(self, event):
        event_data = event['data']
        service_data = eval(event_data['json_str'])
        org_id_bytes = service_data['orgId']
        org_id = Web3.toText(org_id_bytes).rstrip("\x00")
        return org_id

    def _get_tarnsaction_hash(self, event):
        return event['data']['transactionHash']

    def _get_service_id_from_event(self, event):
        event_data = event['data']
        service_data = eval(event_data['json_str'])
        service_id_bytes = service_data['serviceId']
        service_id = Web3.toText(service_id_bytes).rstrip("\x00")
        return service_id

    def _get_metadata_uri_from_event(self, event):
        event_data = event['data']
        service_data = eval(event_data['json_str'])
        metadata_uri = Web3.toText(service_data['metadataURI'])[7:].rstrip("\u0000")
        return metadata_uri

    def _get_registry_contract(self):
        net_id = NETWORK_ID
        base_contract_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'node_modules', 'singularitynet-platform-contracts'))
        registry_contract = self._blockchain_util.get_contract_instance(base_contract_path, "REGISTRY", net_id)
        return registry_contract

    def _get_service_details_from_blockchain(self, event):
        logger.info(f"processing service event {event}")

        registry_contract = self._get_registry_contract()
        org_id = self._get_org_id_from_event(event)
        service_id = self._get_service_id_from_event(event)

        tags_data = self._fetch_tags(
            registry_contract=registry_contract, org_id_hex=org_id.encode("utf-8"),
            service_id_hex=service_id.encode("utf-8"))
        transaction_hash= self._get_tarnsaction_hash(event)

        return org_id, service_id, tags_data ,transaction_hash


class ServiceCreatedEventConsumer(ServiceEventConsumer):

    def on_event(self, event):
        org_id, service_id, tags_data ,transaction_hash = self._get_service_details_from_blockchain(event)
        metadata_uri = self._get_metadata_uri_from_event(event)
        service_ipfs_data = self._ipfs_util.read_file_from_ipfs(metadata_uri)
        self._process_service_data(org_id=org_id, service_id=service_id,
                                   service_metadata=service_ipfs_data, tags_data=tags_data,transaction_hash=transaction_hash)

    def _get_existing_service_details(self, org_id, service_id):
        org_uuid, existing_service = self._service_repository.get_service_for_given_service_id_and_org_id(org_id,
                                                                                                          service_id)

        return org_uuid, existing_service

    def _is_same_transaction(self):
        pass

    def _add_validation_attribute_to_endpoint(self, groups):

        for group in groups:
            changed_endpoints = {}
            for index in range(len(group['endpoints'])):
                changed_endpoints[group['endpoints'][index]] = {'valid': False}
            group['endpoints'] = changed_endpoints




    def _process_service_data(self, org_id, service_id, service_metadata, tags_data,transaction_hash):

        org_uuid, existing_service = self._get_existing_service_details(org_id, service_id)
        service_uuid = str(uuid4())
        display_name = service_metadata.get("display_name", "")
        short_description = service_metadata.get("short_description", "")
        description = service_metadata.get("description", "")
        project_url = service_metadata.get("project_url", "")
        proto = service_metadata.get("project_url", "")
        assets = ServiceFactory.parse_service_metadata_assets(
            service_metadata.get("assets", {}), None)
        mpe_address = service_metadata.get("mpe_address", "")
        metadata_ipfs_hash = service_metadata.get("metadata_ipfs_hash", "")
        contributors = service_metadata.get("contributors", [])
        state = \
            ServiceFactory.create_service_state_entity_model(org_uuid, service_uuid,
                                                             getattr(ServiceStatus, "PUBLISHED_UNAPPROVED").value)

        self._add_validation_attribute_to_endpoint(service_metadata.get("groups", []))
        groups = [
            ServiceFactory.create_service_group_entity_model_for_service_metadata(org_uuid, service_uuid, group) for group in
            service_metadata.get("groups", [])]

        if existing_service:
            existing_service.display_name = display_name
            existing_service.short_description = short_description
            existing_service.description = description
            existing_service.project_url = project_url
            existing_service.proto = proto
            existing_service.assets = ServiceFactory.parse_service_metadata_assets(assets, existing_service.assets)
            existing_service.mpe_address = mpe_address
            existing_service.metadata_ipfs_hash = metadata_ipfs_hash
            existing_service.contributors = contributors
            existing_service.tags = tags_data
            existing_service.groups = [
                ServiceFactory.create_service_group_entity_model_for_service_metadata(org_uuid, existing_service.uuid, group) for group in
                service_metadata.get("groups", [])]



        recieved_service = Service(
            org_uuid, str(uuid4()), service_id, display_name, short_description,
            description, project_url,
            proto, assets,
            DEFAULT_SERVICE_RANKING,
            {}, contributors,
            tags_data,
            mpe_address, metadata_ipfs_hash,
            groups,
            state)

        if not existing_service:
            self._service_repository.add_service(recieved_service, BLOCKCHAIN_USER)

        elif existing_service.service_state.transaction_hash != transaction_hash and existing_service.is_major_change(recieved_service):
            self._service_repository.save_service(BLOCKCHAIN_USER, existing_service, ServiceStatus.DRAFT.value)
        else:
            self._service_repository.save_service(BLOCKCHAIN_USER, existing_service, ServiceStatus.PUBLISHED.value)



