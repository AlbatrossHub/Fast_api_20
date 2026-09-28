# Fast_api_20: FastAPI for Odoo 20

This repo lets any Odoo 20 project serve REST APIs written with
[FastAPI](https://fastapi.tiangolo.com/). It holds OCA's `fastapi` and
`endpoint_route_handler` addons, ported from 19.0 to Odoo 20 in-house because
OCA has not published 20.0 releases yet (PyPI checked on 2026-09-28).

The port was done during the sudi 19 → 20 migration. This repo is the
standalone, reusable copy.

- **Location:** `/opt/odoo20/custom/Fast_api_20` (the same folder as
  `/home/om1203/opt/odoo20/custom/Fast_api_20`)
- **Remote:** `https://github.com/AlbatrossHub/Fast_api_20`
- **License:** LGPL-3 (OCA)

```
Fast_api_20/
├── fastapi/                  addon: FastAPI apps served by Odoo (OCA/rest-framework)
├── endpoint_route_handler/   addon: runtime route registration (OCA/web-api), fastapi depends on it
├── examples/
│   └── fastapi_starter/      template for a project API: copy it, rename it, add your routers
├── requirements.txt          Python packages for the Odoo venv
├── PORTING_NOTES.md          every change made to the OCA 19.0 code, with the reason
└── README.md
```

`examples/` sits one level down on purpose. Odoo only scans the direct
children of an addons-path folder, so the starter never shows up in Apps
unless you copy it into your project.

## Status

Verified on 2026-09-28 against Odoo 20.0 at commit `97c9c9d7`, Python 3.12:

| Check | Result |
|---|---|
| Fresh database, community only, with just these two addons | 44/44 tests pass |
| Copy of `sudi20_test` (enterprise, `website`, all sudi modules), with sudi's vendored copies swapped for this repo | 179/179 tests pass (endpoint_route_handler 20, fastapi 24, sudi_api 135) |
| `examples/fastapi_starter` installed on the fresh database | 3/3 tests pass |
| Live HTTP, OCA demo app | Basic auth, error mapping (400/401/403/404), `Accept-Language`, `/docs` and `/openapi.json`, multi-segment root path, POST retry that replays the request body |
| Live HTTP, sudi field and customer APIs | health, docs, login → JWT → `/auth/me`, `/sync/pull`, `/devices`, token refresh, a field token refused by the customer API, website pages still served alongside |

## Requirements

- Odoo 20.0, community or enterprise. The addons depend only on `base`.
- These Python packages in the Odoo venv (`requirements.txt`):
  `fastapi` (brings in `starlette` and `pydantic`), `python-multipart`,
  `ujson`, `a2wsgi`, `parse-accept-language`. Running the tests also needs
  `httpx2`, because starlette 1.6's `TestClient` imports it instead of `httpx`.

## Add it to an Odoo 20 project

1. **Get the code** next to the project's other custom addons:

   ```bash
   cd /opt/odoo20/custom
   git clone https://github.com/AlbatrossHub/Fast_api_20.git
   ```

2. **Install the Python packages** into the venv that runs Odoo:

   ```bash
   /opt/odoo20/odoo20-venv/bin/pip install -r /opt/odoo20/custom/Fast_api_20/requirements.txt
   ```

3. **Add the folder to the addons path.** Put it before any other folder that
   also contains a `fastapi` or `endpoint_route_handler`, because Odoo uses the
   first copy it finds.

   ```bash
   odoo-bin --addons-path=/opt/odoo20/odoo20/addons,/opt/odoo20/ent,/opt/odoo20/custom/Fast_api_20,/opt/odoo20/custom/<project> ...
   ```

   Or in `odoo.conf`:

   ```ini
   addons_path = /opt/odoo20/odoo20/addons,/opt/odoo20/ent,/opt/odoo20/custom/Fast_api_20,/opt/odoo20/custom/<project>
   ```

4. **If the server hosts more than one database**, load `fastapi` server-wide.
   See [Choosing the database](#choosing-the-database) for why.

   ```ini
   server_wide_modules = base,rpc,web,fastapi
   ```

5. **Restart Odoo**, click *Update Apps List*, and install your API module
   (next section). Installing it pulls in `fastapi` and
   `endpoint_route_handler`. You can also install **Odoo FastAPI** on its own.
   Endpoints are managed in the top-level **FastAPI** app menu. The *FastAPI /
   User* group can see it, and editing needs *FastAPI / Administrator*, which
   the admin user gets on install.

## Build your project's API

Start from the starter:

```bash
cp -r /opt/odoo20/custom/Fast_api_20/examples/fastapi_starter /opt/odoo20/custom/<project>/<project>_api
```

Then, in the copy:

1. Rename the module. Change `fastapi_starter` in the `env.ref()` call in
   `hooks.py` and in the test's `env.ref()` calls, and edit the manifest's
   `name`, `author` and `depends` (add your business modules).
2. `models/fastapi_endpoint.py`: rename the `app` key `starter`. List your
   routers in `_get_fastapi_routers()`. In `_get_app()`, choose how callers
   authenticate. The starter uses HTTP Basic with Odoo logins; replace the
   override with an API-key or JWT implementation if you need one
   (`sudi_api` is a full JWT example).
3. `data/fastapi_endpoint.xml`: set `root_path` (for example
   `/api/<project>/v1`) and rename the runner user. For a stateless API
   (JWT or API keys), add `<field name="save_http_session" eval="False"/>`.
4. `routers/`: write normal FastAPI routers. Get Odoo through dependencies
   from `odoo.addons.fastapi.dependencies`: `odoo_env`,
   `authenticated_partner`, `authenticated_partner_env`, `paging`.
5. `tests/`: `FastAPITransactionCase` (from `odoo.addons.fastapi.tests.common`)
   runs a router in-process with a chosen running user and authenticated
   partner.

How the pieces fit together:

- **An endpoint only serves once it is synced.** `fastapi.endpoint` records
  become routes when `registry_sync` is on. Creating the record is not
  enough. The starter's `post_init_hook` calls `action_sync_registry()`; you
  can also click *Sync Registry* on the endpoint form. OCA's own demo
  endpoints ship unsynced, so they return 404 until you sync them.
- **The runner user** (`user_id` on the endpoint) is the identity the app
  runs as before authentication. Give it only the *FastAPI Endpoint Runner*
  group, or a group that implies it. That group can read its own user and
  endpoint, plus the partner your auth dependency authenticated. In Odoo 20,
  grants from different groups add up, so a runner that is also an internal
  user would get internal rights.
- **Changes reach every worker.** Editing `root_path`, `save_http_session` or
  `route_group`, or any field your module lists in `_fastapi_app_fields()`,
  resets the cached FastAPI apps in every worker at the next request, through
  Odoo's cache signaling. Changing `user_id` refreshes the running user. If
  your module adds settings fields (an auth method, for example), add them to
  `_fastapi_app_fields()` as OCA's demo does. Python changes still need a
  restart.

## Choosing the database

An API request has to resolve to a database before FastAPI runs. Odoo 20
tries these in order, and every candidate must pass `--db-filter`:

1. the session cookie's database
2. the **`X-Odoo-Database` header** (Odoo 20 core, stateless)
3. the only database, if the filter leaves just one
4. `?db=<name>` in the query string (this addon's `patch.py`)
5. `?db=<name>` in the `Referer` header, so Swagger UI's follow-up requests
   work (`patch.py`)

On a single-database or strictly filtered server (for example
`dbfilter = ^%d$`), step 3 covers everything.

On a multi-database server, have your apps send `X-Odoo-Database`, which
always works. The `?db=` fallback lives in the fastapi addon's Python code,
which Odoo only imports once some database with the addon has loaded in that
worker process. Until then, `?db=` requests get 404. Adding `fastapi` to
`server_wide_modules` imports it at startup. This was verified: without it,
a cold `?db=` request returned 404; with it, 200.

## Things that look wrong but are not

- **A 401 from HTTP Basic logs `ERROR ... Exception during request handling`
  with a traceback.** The client still gets a correct 401. Odoo logs any
  non-werkzeug exception this way, and 19.0 behaves the same.
- **On a server with several API databases, the app pool rebuilds whenever
  traffic moves between databases.** The pool's cache sequences are global
  rather than per database. This costs some performance, not correctness, and
  it is upstream behaviour.

## Running the tests

Tests run only when a module is installed or updated. Use a throwaway
database, and always pass `--max-cron-threads=0` to test servers: without it,
the cron thread also processes every other Odoo 20 database on the machine.

```bash
/opt/odoo20/odoo20-venv/bin/python /opt/odoo20/odoo20/odoo-bin server \
  -d fastapi_test -i fastapi \
  --addons-path=/opt/odoo20/odoo20/addons,/opt/odoo20/custom/Fast_api_20 \
  --test-enable --test-tags /fastapi,/endpoint_route_handler \
  --stop-after-init --max-cron-threads=0 --http-port=8189
```

For the starter, add `/opt/odoo20/custom/Fast_api_20/examples` to the addons
path and use `-i fastapi_starter --test-tags /fastapi_starter`.

## Relation to sudi_20

`sudi_20` still carries its own vendored copies of the two addons. Their
runtime code is identical to this repo, and only three test files differ
(see `PORTING_NOTES.md`). They were not touched.

To make sudi use this repo instead: add `Fast_api_20` to its addons path,
delete `sudi_20/fastapi` and `sudi_20/endpoint_route_handler`, then run
`-u fastapi`. This swap was tested on a copy of `sudi20_test`: all 179 tests
passed and the live field and customer APIs worked.

## When OCA releases 20.0

1. `pip install odoo-addon-fastapi odoo-addon-endpoint_route_handler` for
   20.0 into the venv.
2. Diff their code against `PORTING_NOTES.md`, especially the `ir.access`
   rows, `patch.py` and the cache invalidation.
3. Remove `Fast_api_20` from the addons path and run `-u fastapi`. Project
   API modules (the starter, `sudi_api`) keep working unchanged, because they
   only depend on `fastapi`.
