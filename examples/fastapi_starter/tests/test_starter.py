from odoo.tests import tagged

from odoo.addons.fastapi.tests.common import FastAPITransactionCase

from ..routers import starter_router


@tagged("post_install", "-at_install")
class TestStarterApi(FastAPITransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_fastapi_router = starter_router
        cls.default_fastapi_running_user = cls.env.ref(
            "fastapi_starter.starter_api_runner"
        )
        cls.default_fastapi_authenticated_partner = cls.env["res.partner"].create(
            {"name": "Starter Caller", "email": "caller@example.com"}
        )

    def test_health(self):
        with self._create_test_client() as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_me_returns_the_authenticated_partner(self):
        partner = self.default_fastapi_authenticated_partner
        with self._create_test_client() as client:
            response = client.get("/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": partner.id, "name": "Starter Caller", "email": "caller@example.com"},
        )

    def test_endpoint_is_routed(self):
        endpoint = self.env.ref("fastapi_starter.starter_endpoint")
        self.assertTrue(endpoint.registry_sync)
