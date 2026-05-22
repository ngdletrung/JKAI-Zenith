from core.utils.model_router import ModelRouter
r = ModelRouter('/intelligence/rule_hardware.md')
roles = ['PLANNER','SUMMARIZER','EXECUTOR','EXECUTOR_ALPHA','EXECUTOR_BETA','CRITIC']
for role in roles:
    cfg = r.get_role_config(role)
    model = cfg.get("model")
    ctx = cfg.get("options", {}).get("num_ctx")
    ka = cfg.get("keep_alive")
    print("[" + role + "] model=" + str(model) + "  ctx=" + str(ctx) + "  keep_alive=" + str(ka))
