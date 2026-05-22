import importlib
import importlib.util
import os
import sys
import asyncio
import inspect
import re
import redis  # SỬA LỖI: Thiếu thư viện kết nối Redis trung tâm

class ToolRouter:
    """
    BỘ ĐIỀU PHỐI CÔNG CỤ JKAI: Kết nối logic Executor với các module tool_impls.
    """
    def __init__(self):
        # 🔗 [SOVEREIGN-INFRA]: Kết nối Redis trung tâm
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self._redis_conn = None
        self._init_redis()
        
        self._module_cache = {}
        self.skills_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligence", "skills"))
        self._dynamic_tool_map = None  # 🧠 Bản đồ nơ-ron động

        # Pre-compile regex để tăng tốc độ truy quét cấu trúc file logic.py
        self._func_regex = re.compile(r'^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)

    def _init_redis(self):
        try:
            self._redis_conn = redis.Redis(
                host=self.redis_host, port=6379, db=0,
                password=self.redis_password, decode_responses=True,
                socket_connect_timeout=5, socket_timeout=10
            )
        except Exception as e:
            print(f"⚠️ [ROUTER-REDIS-WARN] Khởi tạo Redis thất bại: {e}")
            self._redis_conn = None

    def _find_tool_in_module(self, module, tool_name):
        """🧠 Định vị hàm bằng công nghệ Quét Sâu (Deep Scan)"""
        # 1. Tìm ở cấp độ module (exact match)
        if hasattr(module, tool_name):
            attr = getattr(module, tool_name)
            if inspect.isroutine(attr):
                return attr
                
        # 2. Tìm trong các Instance (đối tượng) có sẵn trong module (VD: _instance)
        for name, obj in inspect.getmembers(module):
            if inspect.ismodule(obj) or inspect.isclass(obj): 
                continue
            if hasattr(obj, tool_name):
                method = getattr(obj, tool_name)
                if inspect.ismethod(method) or inspect.isroutine(method):
                    return method
                    
        # 3. Tự động tìm Class, khởi tạo (Lazy Init) và lấy hàm
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if getattr(cls, '__module__', None) == module.__name__:
                if hasattr(cls, tool_name):
                    try:
                        instance = cls()
                        method = getattr(instance, tool_name)
                        if inspect.ismethod(method) or inspect.isroutine(method):
                            setattr(module, f"_auto_jkai_{cls.__name__}", instance)
                            return method
                    except Exception as e:
                        print(f"⚠️ [ROUTER-AUTO-INIT] Không thể tự khởi tạo {cls.__name__}: {e}")

        # 4. 🔗 [CASE-INSENSITIVE FALLBACK]: Khớp tên hàm bất kể viết hoa/thường
        tool_name_lower = tool_name.lower()
        for attr_name in dir(module):
            if attr_name.lower() == tool_name_lower:
                attr = getattr(module, attr_name)
                if inspect.isroutine(attr):
                    print(f"🔗 [ROUTER-CASE-FIX]: '{tool_name}' → khớp hàm '{attr_name}' theo case-insensitive")
                    return attr
        return None

    def _build_dynamic_tool_map(self, all_skills: dict) -> dict:
        """🔍 [AUTO-DISCOVERY]: Trí tuệ tự động định vị hàm trong logic.py."""
        dynamic_map = {}
        for skill_id, skill_info in all_skills.items():
            rel_path = skill_info.get("rel_path", "")
            if not rel_path: 
                continue
            
            # Chuẩn hóa đường dẫn tương thích đa nền tảng
            rel_path_clean = rel_path.replace("\\", "/")
            skill_dir = os.path.dirname(rel_path_clean)
            
            # Khớp chính xác logic_file theo cấu trúc thư mục dạng cây của skill
            logic_file = os.path.join(self.skills_root, os.path.basename(skill_dir), "logic.py")
            if not os.path.exists(logic_file):
                # Dự phòng tìm trực tiếp theo cấu trúc tương đối đầy đủ từ hệ thống registry
                base_parent = os.path.dirname(self.skills_root)
                logic_file = os.path.normpath(os.path.join(base_parent, rel_path_clean, "..", "logic.py"))
                if not os.path.exists(logic_file): 
                    continue
                
            try:
                with open(logic_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Truy quét toàn bộ hàm (def) không phải private dựa trên regex pre-compiled
                    matches = self._func_regex.finditer(content)
                    for match in matches:
                        func_name = match.group(1)
                        if not func_name.startswith('_'):
                            dynamic_map[func_name] = skill_id
                            # 🛡️ [CASE-INSENSITIVE MAP]: Lưu cả key viết thường để khớp mọi biến thể hoa/thường từ control-plane
                            dynamic_map[func_name.lower()] = skill_id
            except Exception as e:
                print(f"⚠️ [ROUTER-DISCOVERY] Lỗi khi quét map từ file {logic_file}: {e}")
        
        self._dynamic_tool_map = dynamic_map
        return dynamic_map

    async def call_tool(self, tool_name: str, **kwargs):
        print(f"🔌 [JKAI-ROUTER] Centralized Routing to: {tool_name}")

        # 🛡️ [STOP-CHECK]: Kiểm tra Phản xạ Dừng khẩn cấp trước khi thực thi
        if self._redis_conn:
            try:
                stop_sig = self._redis_conn.get("agent:stop_signal")
                if stop_sig in ['true', '1', b'true']:
                    print(f"🛑 [ROUTER] Execution cancelled by Master for tool: {tool_name}")
                    return {"status": "error", "msg": "🛑 [STOPPED]: Tiến trình thực thi đã bị Master ngắt quãng."}
            except Exception as redis_err: 
                print(f"⚠️ [ROUTER-REDIS-WARN]: Không thể check stop_signal: {redis_err}")

        try:
            # 🧪 [ADR-100]: Lazy-Load shared lookup
            from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator
            orchestrator = JKAIKnowledgeOrchestrator()
            all_skills = await orchestrator.get_all_skills_dict()
            
            # 🧠 [DYNAMIC-RESOLVER]: Khớp nối thông minh
            if self._dynamic_tool_map is None:
                self._build_dynamic_tool_map(all_skills)

            resolved_tool_name = tool_name
            if tool_name in self._dynamic_tool_map:
                resolved_tool_name = self._dynamic_tool_map[tool_name]
            elif tool_name.lower() in self._dynamic_tool_map:
                resolved_tool_name = self._dynamic_tool_map[tool_name.lower()]
            
            skill_info = all_skills.get(resolved_tool_name)
            if not skill_info:
                # 🔄 [CASE-NORMALIZE]: Thử khớp với UPPERCASE (skill ID trong registry thường là UPPER_CASE)
                resolved_upper = resolved_tool_name.upper()
                skill_info = all_skills.get(resolved_upper)
                if skill_info:
                    print(f"🔗 [ROUTER-CASE-FIX]: '{resolved_tool_name}' → khớp registry key '{resolved_upper}'")
                    resolved_tool_name = resolved_upper
            
            if not skill_info:
                # 📡 [AUTO-SYNC-PROTOCOL]: Nếu không thấy, tự động tái thiết bản đồ nơ-ron
                print(f"🔄 [ROUTER-SYNC]: Kỹ năng '{resolved_tool_name}' chưa có trong bản đồ. Đang tự động đồng bộ...")
                all_skills_full = await orchestrator.sync_sovereign_registry()
                all_skills = all_skills_full.get("skills", {})
                skill_info = all_skills.get(resolved_tool_name) or all_skills.get(resolved_tool_name.upper())
                # 🛡️ [SYSTEMIC-REBUILD]: Tái cấu trúc bản đồ nơ-ron động ngay lập tức để cập nhật các hàm mới
                self._build_dynamic_tool_map(all_skills)
                
            if not skill_info:
                # Thử tìm theo name/id case-insensitive nếu key vẫn không khớp
                for s_id, s_data in all_skills.items():
                    s_id_str = str(s_data.get("id") or "")
                    s_name_str = str(s_data.get("name") or "")
                    if s_id_str.upper() == resolved_tool_name.upper() or s_name_str.upper() == resolved_tool_name.upper():
                        skill_info = s_data
                        break
            
            if not skill_info:
                return {"status": "error", "msg": f"Tool '{tool_name}' (resolved as '{resolved_tool_name}') not found in registry."}

            # 🧬 [SOVEREIGN-PATH-RESOLVER]: Ưu tiên rel_path từ Registry
            rel_path = skill_info.get("rel_path", "")
            if rel_path:
                rel_path = rel_path.replace("\\", "/") # Chuẩn hóa path chéo hệ điều hành
                skill_dir = os.path.dirname(rel_path)
                skill_folder = os.path.basename(skill_dir)
                
                # 🛡️ [SOVEREIGN-PATH-ALIGNMENT]: Định vị đường dẫn chuẩn cấu trúc container
                # parent của self.skills_root là '/app/intelligence' chứa thư mục 'skills'
                intelligence_dir = os.path.dirname(self.skills_root)
                logic_file = os.path.normpath(os.path.join(intelligence_dir, rel_path, "..", "logic.py"))
                
                # Nếu không thấy ở cấu trúc chuẩn, thử ở skills_root
                if not os.path.exists(logic_file):
                    logic_file = os.path.join(self.skills_root, skill_folder, "logic.py")
            else:
                skill_folder = skill_info.get("name") or tool_name
                logic_file = os.path.join(self.skills_root, skill_folder, "logic.py")
            
            if not os.path.exists(logic_file):
                return {"status": "error", "msg": f"Logic file for '{tool_name}' not found at {logic_file}. Path sync required."}

            # 🚀 [QUANTUM-LOAD]: Nạp module trực tiếp từ path đã định danh
            cache_key = skill_folder
            target_func = None

            if cache_key in self._module_cache:
                module = self._module_cache[cache_key]
                target_func = self._find_tool_in_module(module, tool_name)
            
            if not target_func:
                spec = importlib.util.spec_from_file_location(f"{skill_folder}.logic", logic_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module.__name__] = module
                spec.loader.exec_module(module)
                self._module_cache[cache_key] = module
                target_func = self._find_tool_in_module(module, tool_name)

            if not target_func:
                return {"status": "error", "msg": f"Tool function '{tool_name}' not found in {logic_file}."}
            
            sig = inspect.signature(target_func)
            
            # 🎯 GIAO THỨC TƯƠNG THÍCH NGƯỢC KW_ARGS
            if "profile" in kwargs and "profile" not in sig.parameters and not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                kwargs.pop("profile", None)

            # 🧬 [AUTO-HEALING]: Tự động ánh xạ & tự chữa lành tham số thông minh
            required_params = [p.name for p in sig.parameters.values() if p.default == inspect.Parameter.empty and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)]
            
            if "query" in required_params and "query" not in kwargs:
                for synonym in ["search_query", "q", "search", "topic", "text", "url_or_query"]:
                    if synonym in kwargs:
                        kwargs["query"] = kwargs.pop(synonym)
                        print(f"🧬 [ROUTER-AUTO-HEAL]: Tự động ánh xạ tham số '{synonym}' -> 'query'.")
                        break
            
            # [GENERIC-FALLBACK]: Nếu chỉ có duy nhất 1 tham số bắt buộc, và kwargs chứa 1 tham số không khớp tên, tự động map
            if len(required_params) == 1 and required_params[0] not in kwargs:
                other_keys = [k for k in kwargs.keys() if k not in ["task_id", "trace_id", "session_id"]]
                if len(other_keys) == 1:
                    single_key = other_keys[0]
                    kwargs[required_params[0]] = kwargs.pop(single_key)
                    print(f"🧬 [ROUTER-AUTO-HEAL]: Tự động ánh xạ tham số duy nhất '{single_key}' -> '{required_params[0]}'.")

            # Lọc bỏ các kwargs không hợp lệ nếu hàm không nhận **kwargs
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_var_keyword:
                valid_params = set(sig.parameters.keys())
                kwargs = {k: v for k, v in kwargs.items() if k in valid_params}

            # Thực thi dựa trên định dạng Async/Sync của Target Function
            if asyncio.iscoroutinefunction(target_func):
                return await target_func(**kwargs)
            return target_func(**kwargs)
            
        except Exception as e:
            import traceback
            print(f"❌ [ROUTER-CRITICAL-ERROR]: {traceback.format_exc()}")
            return {"status": "error", "msg": f"Router failed: {str(e)}"}

    def invalidate_cache(self):
        """Xóa cache module để buộc nạp lại từ disk."""
        # Fix leak sys.modules
        for cache_key, module in self._module_cache.items():
            if module.__name__ in sys.modules:
                del sys.modules[module.__name__]
        self._module_cache.clear()
        self._dynamic_tool_map = None # Xóa luôn bản đồ động
        print("🔄 [JKAI-ROUTER] Module & Dynamic Map cache invalidated. Mức độ an toàn bộ nhớ: Tối đa.")
