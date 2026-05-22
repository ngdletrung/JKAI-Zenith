"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH — PLANNER v2.0 PATCH (generate_plan upgrade)                  ║
║  Drop-in replacement cho generate_plan() trong planner.py hiện tại.        ║
║  Tích hợp: FailureMemory · ExecutionPolicy · CognitiveGuardrails           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Cách dùng:
  Thay thế toàn bộ method generate_plan() trong class Planner bằng đoạn này.
  Hoặc copy từng block có comment "PATCH:" vào đúng vị trí trong code gốc.
"""

# ─── IMPORTS CẦN THÊM VÀO ĐẦU FILE planner.py ──────────────────────────────
# from failure_memory import failure_memory, FailureStage, init_failure_memory
# from execution_policy import get_policy_engine, WorldState
# from cognitive_guardrails import guardrail_registry, GuardrailException
# import psutil  # (đã có trong planner.py gốc)


async def generate_plan_v2(
    self,
    goal:     str,
    context:  dict,
    images    = None,
    history   = None,
    task_id:  str = "system",
) -> dict:
    """
    generate_plan() v2.0 — với Cognitive Intelligence layer.

    Thay đổi so với v1:
      [+] Pre-flight failure check (FailureMemory)
      [+] Guardrail injection vào mỗi replan attempt
      [+] Execution policies resolve sau khi plan được approved
      [+] Critic loop hard limit (không debate vô hạn)
      [+] Token budget tracking
    """
    # ── KHỞI TẠO ────────────────────────────────────────────────────────────
    complexity = self._estimate_complexity(goal)
    skills_summary = self.orchestrator.get_all_skills_summary()

    # PATCH: Khởi tạo Guardrails cho task này
    def _on_guardrail_violation(tid, v):
        self._log("GUARDRAIL", f"[{v.violation.upper()}]: {v.reason}", tid)

    guard = guardrail_registry.get_or_create(task_id, on_violation=_on_guardrail_violation)

    # ── PHASE 1: PRE-FLIGHT CHECK ────────────────────────────────────────────
    # PATCH: Kiểm tra failure patterns trước khi bắt đầu — zero LLM cost
    task_type = context.get("task_type", "general")
    pre_flight = await failure_memory.pre_flight_check(goal, task_type)

    if pre_flight.has_warnings:
        context["pre_flight_warnings"] = failure_memory.format_for_planner(pre_flight)
        context["pre_flight_risk"]     = pre_flight.risk_level
        if pre_flight.suggested_steps:
            context["suggested_prevention"] = pre_flight.suggested_steps
        self._log(
            "PLANNER",
            f"[PRE-FLIGHT]: {pre_flight.patterns_found} risk patterns | level={pre_flight.risk_level}",
            task_id,
        )

    # ── PHASE 2: DISPATCHER + KNOWLEDGE (giữ nguyên từ v1) ──────────────────
    from dispatcher import Dispatcher
    dispatcher   = Dispatcher()
    dispatch_res = await dispatcher.dispatch(goal, task_id=task_id)

    skill_dna          = ""
    knowledge_context  = dispatch_res.get("knowledge_context", "")
    candidates         = dispatch_res.get("candidates", [])
    if candidates:
        for c in candidates:
            skill_dna += f"- {c['skill']} (Tier: {c['tier']}, Rating: {c['rating']})\n"

    manifesto = await knowledge_brain.ask(
        "JKAI Zenith corporate manifesto sovereign identity", tier=1, task_id=task_id
    )

    if knowledge_context:
        context["obsidian_knowledge"] = knowledge_context

    insights = engine.get_insights(task_id)
    if insights:
        context["global_insights"] = insights

    # World state (giữ nguyên)
    import psutil
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram_usage = psutil.virtual_memory().percent
    world_state_data = f"- CPU Load: {cpu_usage}%\n- RAM Usage: {ram_usage}%"
    if cpu_usage > 85 or ram_usage > 90:
        world_state_data += "\n⚠️ [CRITICAL] HỆ THỐNG QUÁ TẢI."
    context["world_state"] = world_state_data

    # ── PHASE 3: BUILD SYSTEM PROMPT ────────────────────────────────────────
    is_fast_mode = (dispatch_res.get("mode") == "fast") or (complexity in ["simple", "medium"])
    specialist_prompt = await self._forge.forge_specialist_prompt(
        goal=goal, context=context, skills_summary=skill_dna, fast_mode=is_fast_mode
    )
    system_prompt = self._build_system_prompt(
        manifesto or "", specialist_prompt, skill_dna, complexity, False
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history and len(history) > self._HISTORY_THRESHOLD:
        messages.extend(await self._compress_history(history, task_id))
    elif history:
        messages.extend(history)
    messages.append({"role": "user", "content": goal})

    # ── PHASE 4: PLANNER LOOP với Guardrails ────────────────────────────────
    for attempt in range(1, self._MAX_RETRIES + 1):
        if self._is_aborted():
            return {"status": "aborted"}

        # PATCH: Inject guardrail context vào system prompt (ngắn gọn, không spam)
        guardrail_ctx = guard.inject_context_for_planner()
        if guardrail_ctx:
            messages_with_guard = messages + [{"role": "system", "content": guardrail_ctx}]
        else:
            messages_with_guard = messages

        raw_plan = await engine.call_chat(
            messages=messages_with_guard,
            role="PLANNER",
            schema=Blueprint.model_json_schema(),
            task_id=task_id,
        )

        # PATCH: Track token usage (estimate nếu engine không expose trực tiếp)
        approx_tokens = len(str(raw_plan)) // 4
        token_check   = guard.record_tokens_used(approx_tokens)
        if token_check.should_abort:
            self._log("GUARDRAIL", token_check.reason, task_id)
            break  # Thoát loop, trả về plan tốt nhất

        if raw_plan == "Mission aborted by Master.":
            return {"status": "aborted"}

        try:
            if isinstance(raw_plan, str):
                raw_plan = json.loads(raw_plan)

            blueprint = Blueprint.model_validate(raw_plan)

            if blueprint.ambiguous:
                return blueprint.model_dump()

            # Ghost tool check (giữ nguyên)
            ghosts = await self._verify_integrity(blueprint.model_dump(), task_id)
            if ghosts:
                messages.append({
                    "role": "system",
                    "content": f"Ghost tools detected: {ghosts}. Sửa lại thưa Master.",
                })
                continue

            # PATCH: Pre-flight suggested steps → inject vào plan nếu chưa có
            blueprint = self._inject_prevention_steps(blueprint, pre_flight)

            # PATCH: Critic loop check trước khi gọi critic
            critic_check = guard.check_critic_loop()
            if critic_check.should_abort:
                self._log("GUARDRAIL", critic_check.reason, task_id)
                # Accept plan hiện tại, không debate thêm
                final_plan = blueprint.model_dump()
                final_plan["guardrail_abort"] = True
                final_plan["guardrail_reason"] = critic_check.reason
                return self._attach_policies(final_plan, context, task_id)

            review = await self._critic.review_plan(goal, blueprint.model_dump().get("steps"))

            # Sovereign intervention (giữ nguyên)
            if review.get("needs_nuclear_key") or "PHÊ DUYỆT" in review.get("feedback", ""):
                full_plan = blueprint.model_dump()
                full_plan["needs_approval"] = True
                full_plan["feedback"]       = review.get("feedback")
                self._log("CRITIC", "[KIEM SOAT]: Ke hoach yeu cau Master phe duyet.", task_id)
                return full_plan

            if review.get("approved"):
                plan_summary = f"[STRATEGIC-PLAN]: {blueprint.thought}\n"
                for s in blueprint.steps:
                    plan_summary += f"  - {s.id}: {s.description} ({s.assigned_agent})\n"
                self._log("THOUGHT", plan_summary, task_id)

                # PATCH: Attach execution policies vào plan đã approved
                return self._attach_policies(blueprint.model_dump(), context, task_id)

            # PATCH: Replan check
            replan_check = guard.check_before_replan(blueprint.model_dump().get("steps", []))
            if replan_check.should_abort:
                self._log("GUARDRAIL", replan_check.reason, task_id)
                final_plan           = blueprint.model_dump()
                final_plan["feedback"] = review.get("feedback")
                final_plan["guardrail_note"] = replan_check.suggested_action
                return self._attach_policies(final_plan, context, task_id)

            if attempt == self._MAX_RETRIES:
                self._log("SYSTEM", "[DEBATE-LIMIT]: Trinh phuong an cuoi cung.", task_id)
                final_plan             = blueprint.model_dump()
                final_plan["feedback"] = review.get("feedback")
                return self._attach_policies(final_plan, context, task_id)

            messages.append({
                "role": "system",
                "content": f"Feedback từ CRITIC: {review.get('feedback')}. Điều chỉnh kế hoạch thưa Master.",
            })

        except Exception as e:
            messages.append({"role": "system", "content": f"Schema error: {e}"})

    # Đóng guardrail session
    guardrail_registry.close(task_id)
    return {"status": "failed"}


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER METHODS — Thêm vào class Planner
# ─────────────────────────────────────────────────────────────────────────────

def _inject_prevention_steps(self, blueprint, pre_flight) -> object:
    """
    Tự động thêm prevention steps từ FailureMemory vào đầu plan,
    nhưng chỉ nếu plan chưa có step tương tự.
    """
    if not pre_flight.has_warnings or not pre_flight.suggested_steps:
        return blueprint

    existing_descriptions = {s.description.lower() for s in blueprint.steps}
    injected_count = 0

    for sug in pre_flight.suggested_steps:
        # Tránh duplicate
        if any(word in existing_descriptions
               for word in sug["description"].lower().split()[:3]):
            continue

        # Import PlanStep để tạo step mới
        # from planner import PlanStep, HardwareTarget  # đã import ở đầu file
        prevention_step = {
            "id":              f"pre_prevent_{sug['stage']}_{injected_count:02d}",
            "tool":            "skill_validate_environment",  # Hoặc tool phù hợp
            "args":            {},
            "description":     sug["description"],
            "assigned_agent":  "agent_executor_beta.md",
            "hardware_target": "BETA",
            "expert_mindset":  "Kiểm tra trước khi hành động. Phòng hơn chữa.",
            "verification":    "Môi trường sạch, dependencies đủ, không có blocker",
            "parallel":        False,
            "depends_on":      [],
            "fallback_tool":   None,
        }
        blueprint.steps.insert(0, prevention_step)
        injected_count += 1

        if injected_count >= 2:  # Không thêm quá 2 prevention steps
            break

    return blueprint


def _attach_policies(self, plan: dict, context: dict, task_id: str) -> dict:
    """
    Gắn execution policies vào từng step của plan.
    Executor dùng policies này để quyết định timeout, retry, model...
    """
    try:
        import psutil
        from execution_policy import get_policy_engine, WorldState

        ws = WorldState(
            cpu_percent    = psutil.cpu_percent(),
            ram_percent    = psutil.virtual_memory().percent,
        )
        policy_engine = get_policy_engine()
        steps = plan.get("steps", [])

        if steps:
            policies = policy_engine.resolve_batch(steps, context, ws)
            plan["execution_policies"] = {
                sid: {
                    "model":          p.preferred_model,
                    "depth":          p.reasoning_depth.value,
                    "timeout":        p.timeout,
                    "max_retry":      p.max_retry,
                    "use_critic":     p.use_critic,
                    "use_verifier":   p.use_verifier,
                    "risk_level":     p.risk_level,
                    "verification":   p.verification_level.value,
                    "rationale":      p.rationale,
                }
                for sid, p in policies.items()
            }
            self._log(
                "POLICY",
                f"[POLICIES ATTACHED]: {len(steps)} steps với execution policies.",
                task_id,
            )
    except Exception as e:
        logger.warning(f"[POLICY-ATTACH]: Failed to attach policies: {e}")

    return plan


# ─────────────────────────────────────────────────────────────────────────────
#  CHECKLIST TÍCH HỢP ĐẦY ĐỦ
# ─────────────────────────────────────────────────────────────────────────────
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CHECKLIST TÍCH HỢP 3 MODULE VÀO JKAI ZENITH                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  BƯỚC 1: Copy 3 file mới vào project                                        ║
║    ✓ failure_memory.py      → jkai/core/utils/                              ║
║    ✓ execution_policy.py    → jkai/core/utils/                              ║
║    ✓ cognitive_guardrails.py → jkai/core/utils/                             ║
║                                                                              ║
║  BƯỚC 2: Khởi tạo FailureMemory trong app startup                           ║
║    from failure_memory import init_failure_memory                            ║
║    from redis_client import redis_client as rc                               ║
║    init_failure_memory(redis_client=rc)                                      ║
║                                                                              ║
║  BƯỚC 3: Thêm imports vào planner.py                                        ║
║    from failure_memory import failure_memory, FailureStage                  ║
║    from execution_policy import get_policy_engine, WorldState               ║
║    from cognitive_guardrails import guardrail_registry                      ║
║                                                                              ║
║  BƯỚC 4: Thêm 2 helper methods vào class Planner                            ║
║    _inject_prevention_steps(self, blueprint, pre_flight)                     ║
║    _attach_policies(self, plan, context, task_id)                           ║
║                                                                              ║
║  BƯỚC 5: Replace generate_plan() bằng generate_plan_v2()                    ║
║    (hoặc patch từng block theo comment "PATCH:")                             ║
║                                                                              ║
║  BƯỚC 6: Trong Executor — ghi nhận failures                                 ║
║    await failure_memory.record_failure(...)    ← sau mỗi tool fail          ║
║    guard.check_before_tool(tool_id, args)     ← trước mỗi tool call        ║
║                                                                              ║
║  BƯỚC 7: Test với 1 task đơn giản, kiểm tra logs:                           ║
║    [PRE-FLIGHT]: ...                                                         ║
║    [POLICIES ATTACHED]: ...                                                  ║
║    [GUARDRAIL]: healthy                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
