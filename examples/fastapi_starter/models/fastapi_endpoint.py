from odoo import fields, models

from odoo.addons.fastapi.dependencies import (
    authenticated_partner_from_basic_auth_user,
    authenticated_partner_impl,
)

from fastapi import APIRouter

from ..routers import starter_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("starter", "Starter API")],
        ondelete={"starter": "cascade"},
    )

    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == "starter":
            return [starter_router]
        return super()._get_fastapi_routers()

    def _get_app(self):
        app = super()._get_app()
        if self.app == "starter":
            # HTTP Basic with an Odoo login and password. To use API keys or
            # JWT instead, point this override at your own implementation.
            app.dependency_overrides[authenticated_partner_impl] = (
                authenticated_partner_from_basic_auth_user
            )
        return app
