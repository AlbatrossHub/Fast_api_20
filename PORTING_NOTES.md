# Porting notes: OCA 19.0 → Odoo 20

Every change from the upstream 19.0 sources, file by file. Use this list when
OCA publishes its own 20.0 releases: diff theirs against this list before you
switch.

Upstream baselines:

- `fastapi`: OCA/rest-framework, PyPI `odoo-addon-fastapi` 19.0.1.1.0.2
- `endpoint_route_handler`: OCA/web-api, PyPI `odoo-addon-endpoint_route_handler` 19.0.1.2.0

The runtime code (everything outside `tests/`) is byte-identical to the
vendored copies in `sudi_20` (`/opt/odoo20/custom/sudi_20/fastapi` and
`/endpoint_route_handler`), where it was first ported. Three test files
differ; see the end of this file.

## endpoint_route_handler

| File | Change | Why |
|---|---|---|
| `__manifest__.py` | Version `20.0.1.2.0`. `security/ir.model.access.csv` is replaced by `security/ir.access.csv`. | Odoo 20 merged `ir.model.access` and `ir.rule` into `ir.access`. The same 8 grants are kept, with `perm_*` flags written as `operation` letters (`crud`, `r`). |
| `registry.py` | Column definitions are wrapped in `SQL(...)`. | v20 `tools.sql.create_model_table()` renders plain strings as quoted literals, so `"VARCHAR"` would become `'VARCHAR'`. |
| `registry.py` | New `invalidate_routing_cache(env)`. | v19 `registry.clear_cache("routing")` was immediate and applied to the whole registry. v20 `env.transaction.invalidate_ormcache("routing")` only affects the current transaction until it commits. The helper does both of these: it invalidates on the transaction (which signals other workers at commit), and it clears the shared `routing` / `routing.rewrites` LRUs in place, as v19 did. |
| `models/endpoint_route_handler.py`, `models/endpoint_route_sync_mixin.py` | `registry.clear_cache("routing")` becomes `invalidate_routing_cache(self.env)`. | See above. |
| `models/ir_http.py` | `@tools.ormcache` becomes `@api.ormcache`. | v20 API. |
| `models/ir_http.py` | `_auth_method_user_endpoint(cls)` becomes `(cls, routing)` and passes `routing` on. | v20 `_auth_method_*` hooks receive the routing dict. |
| `models/ir_http.py` | `SessionExpiredException` is imported from `odoo.http.session`. | `odoo.http` is a package in v20. |
| `tests/test_endpoint.py` | The cross-env test refreshes env2's routing cache layer before asserting. | v20 ormcaches are layered per transaction. A transaction that is already open sees the change at its next signaling check, which every real request performs. |

## fastapi

| File | Change | Why |
|---|---|---|
| `__manifest__.py` | Version `20.0.1.1.0`. `security/fastapi_endpoint.xml` and `security/ir_rule+acl.xml` are replaced by `security/ir.access.csv`. | `ir.access` merge. The view/manage grants are kept as they were. Each of the three "runner" ACL rows is merged with its record rule into one grant that carries the rule's domain. |
| `models/ir_rule.py` becomes `models/ir_access.py` | `_eval_context()` still adds `authenticated_partner_id`. `_compute_domain_keys()` becomes the `_get_access_context()` generator. | v20 hook names. This is the same pattern Odoo 20's `website` module uses. |
| `models/fastapi_endpoint.py` | `registry.clear_cache()` becomes `env.transaction.invalidate_ormcache()` (2 places). `@tools.ormcache` becomes `@api.ormcache` (3 places). | v20 API. The `default` cache sequence still increases at commit, and that is what resets the app pool in every worker. |
| `models/res_lang.py` | `@tools.ormcache` becomes `@api.ormcache`. | v20 API. |
| `fastapi_dispatcher.py` | `Dispatcher` is imported from `odoo.http.dispatcher`. | `odoo.http` is a package in v20. |
| `patch.py` | The v19 method `Request._get_session_and_dbname()`, which returned `(session, db)`, is now the module function `odoo.http.router._set_session_and_dbname(request)`, which sets `request.session` and `request.db` itself. The patch rebinds that module attribute. `db_filter()` is given `host=`. | v20 moved this out of `Request`. The router and `retrying.py` both look the function up on the module when they call it, so rebinding the attribute is enough. |
| `pools/fastapi_app.py` | `registry.cache_sequences` becomes `{name: seq for name, (seq, _) in registry.registry_caches__.items()}`. | v20 registry cache bookkeeping. |
| `routers/demo_router.py` | Local `MAX_TRIES_ON_CONCURRENCY_FAILURE = 5`. | `odoo.service.model` no longer has it. v20 keeps the same constant in `odoo.http.retrying`. |
| `tests/test_db_param.py` | Rewritten for the new patch shape. | Follows `patch.py`. |

Unchanged, and checked against the v20 source: basic auth
(`res.users.authenticate(credential, user_agent_env)`), the `Dispatcher`
abstract methods, `request.make_response` / `make_json_response`,
`HTTPRequest._HTTPRequest__wrapped`, `CommonServer.on_stop`,
`base.models.ir_model.query_insert`, and `tools.sql.create_index` /
`add_constraint`.

Lint nit left on purpose: `tools` is now an unused import in
`fastapi/models/fastapi_endpoint.py`, `fastapi/models/res_lang.py` and
`endpoint_route_handler/models/ir_http.py`. It has no effect. It is kept so the
runtime code stays identical to what sudi_20 runs.

### Behaviour difference from the ir.access merge

In 19.0, a runner-group record rule narrowed access even for a user who also
belonged to another group that granted more. In 20, grants from different
groups add up (union). A runner user who is also an internal user therefore
gets internal access. Keep endpoint runner users dedicated, with only the
runner group (or a group that implies it). OCA already recommends this.

The xmlids of the three old runner ACL records
(`fastapi.res_user_fastapi_running_user`,
`fastapi.res_partner_fastapi_running_user` and
`fastapi.fastapi_endpoint_fastapi_running_user`) no longer exist. Their grants
live on the `*_rule` ids. `fastapi.group_fastapi_endpoint_runner` is unchanged.

## Test-only changes in this repo (not in sudi_20's copy)

| File | Change | Why |
|---|---|---|
| `endpoint_route_handler/tests/common.py` | New `routing_context(env)`, added to the test class context. | When `website` is installed, v20 builds one routing map per host and reads `host_id` from the caller's context whenever a request is active. `MockRequest` only puts it on the request's env, so 4 tests raised `KeyError: 'host_id'` on any DB with `website`. Real requests are not affected. |
| `endpoint_route_handler/tests/test_endpoint.py` | `new_rollbacked_env()` adds the same context. | Same reason, for the cross-env test's second cursor. |
| `endpoint_route_handler/tests/test_registry.py` | The duplicate-key check now violates only the key index. | The old row broke both unique indexes. PostgreSQL reports whichever index it checks first, and a `pg_dump`/restore changes that order, so the test failed on restored copies of a database. |
