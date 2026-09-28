def post_init_hook(env):
    # Routes are only mounted once the endpoint is synced to the route
    # registry; creating the record does not do it.
    env.ref("fastapi_starter.starter_endpoint").action_sync_registry()
