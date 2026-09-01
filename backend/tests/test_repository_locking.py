import unittest
from unittest.mock import Mock

import backend.db_models.favorite
import backend.db_models.inquiry
import backend.db_models.property
import backend.db_models.user
from backend.repositories.inquiry_repository import get_inquiry_for_update
from backend.repositories.property_repository import get_property_for_update


class RepositoryLockingTests(unittest.TestCase):
    def test_inquiry_mutation_query_requests_a_row_lock(self):
        session = Mock()

        get_inquiry_for_update(session, 17)

        statement = session.scalar.call_args.args[0]
        self.assertIsNotNone(statement._for_update_arg)

    def test_property_availability_mutations_request_a_row_lock(self):
        session = Mock()

        get_property_for_update(session, 23)

        statement = session.scalar.call_args.args[0]
        self.assertIsNotNone(statement._for_update_arg)


if __name__ == "__main__":
    unittest.main()
