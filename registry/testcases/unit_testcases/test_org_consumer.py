import unittest
from unittest.mock import patch, Mock
from uuid import uuid4

from future.backports.datetime import datetime

from registry.consumer.organization_event_consumer import OrganizationCreatedEventConsumer
from registry.domain.services.organization_service import OrganizationService
from registry.domain.models.organization import Organization as DomainOrganization
from registry.infrastructure.models.models import Organization, OrganizationReviewWorkflow, OrganizationHistory
from registry.infrastructure.repositories.organization_repository import OrganizationRepository


class TestOrganizationService(unittest.TestCase):

    def setUp(self):
        self.org_service = OrganizationService()
        self.org_repo = OrganizationRepository()
        self.org_event_consumer = OrganizationCreatedEventConsumer("wss://ropsten.infura.io/ws",
                                                                   "http://ipfs.singularitynet.io",
                                                                   80)

    @patch("common.ipfs_util.IPFSUtil", return_value=Mock(write_file_in_ipfs=Mock(return_value="Q3E12")))
    @patch('common.s3_util.S3Util.push_io_bytes_to_s3')
    @patch('common.ipfs_util.IPFSUtil.read_file_from_ipfs')
    @patch('common.ipfs_util.IPFSUtil.read_bytesio_from_ipfs')
    def test_publish_org_ipfs(self, nock_read_bytesio_from_ipfs, mock_ipfs_read, mock_s3_push,mock_ipfs_write):
        #Setup organization in publish in progress state
        test_org_id = uuid4().hex
        username = "dummy@snet.io"
        self.org_repo.add_org_with_status(Organization(
            "dummy_org", "org_id", test_org_id, "organization",
            "that is the dummy org for testcases", "that is the short description", "dummy.com", [], [], ""),
            "PUBLISH_IN_PROGRESS", username)
        #response = OrganizationService().publish_org(test_org_id, username)
        orgs = self.org_repo.get_org_with_status(test_org_id, "PUBLISH_IN_PROGRESS")

        event = {"data": {'row_id': 2, 'block_no': 6243627, 'event': 'OrganizationCreated',
                          'json_str': "{'orgId': b'org_id\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'}",
                          'processed': b'\x00',
                          'transactionHash': "b'y4\\xa4$By/mZ\\x17\\x1d\\xf2\\x18\\xb6aa\\x02\\x1c\\x88P\\x85\\x18w\\x19\\xc9\\x91\\xecX\\xd7E\\x98!'",
                          'logIndex': '1', 'error_code': 1, 'error_msg': '',
                          'row_updated': datetime(2019, 10, 21, 9, 44, 9),
                          'row_created': datetime(2019, 10, 21, 9, 44, 9)}, "name": "OrganizationCreated"}
        nock_read_bytesio_from_ipfs.return_value = ""
        mock_s3_push.return_value = "http://test-s3-push"
        mock_ipfs_read.return_value = {
            "org_name": "dummy_org",
            "org_id": "org_id",
            "metadata_ipfs_hash":"Q3E12",
            "org_type":"organization",

            "contacts": [
            ],
            "description": {
                "description":"that is the dummy org for testcases",
                "short_description":"that is the short description",
                "url":"dummy.com"
            },
            "assets": [],
            "groups": []
        }

        self.org_event_consumer.on_event(event)
        self.org_repo.session.commit()
        published_org=self.org_repo.get_org_with_status(test_org_id,"PUBLISHED")
        assert len(published_org)==1






    def tearDown(self):
        self.org_repo.session.query(Organization).delete()
        self.org_repo.session.query(OrganizationReviewWorkflow).delete()
        self.org_repo.session.query(OrganizationHistory).delete()
        self.org_repo.session.commit()
