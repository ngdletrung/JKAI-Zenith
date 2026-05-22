import re
import json
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any

# ==========================================
# 1. Ý ĐỊNH CỐT LÕI (CORE & ADVANCED INTENTS)
# ==========================================

INTENT_BOOKS = {
    "CREATE": {
        "ancient": ["khởi tạo", "thiết lập", "xây dựng", "tạo lập", "sáng tác", "soạn thảo", "đúc kết", "kiến tạo", "khai sinh", "dựng nên", "hình thành", "chế tác", "tạo ra", "đặt nền", "mở đầu", "phôi thai", "lập nên", "khởi xướng", "kiến thiết", "gây dựng"],
        "modern": ["create", "generate", "build", "set up", "initialize", "new", "produce", "write", "make", "compose", "design", "craft", "draft", "form", "fabricate", "construct", "develop", "launch", "setup", "spawn", "spin up", "deploy"],
        "slang": ["vẽ ra", "làm cho tôi", "tạo hộ", "viết giúp", "build dùm", "tạo đi", "làm đi", "viết cho mình", "phun ra", "đẻ ra", "nặn ra", "chế ra", "cào ra", "múa code", "lên dàn", "triển luôn"],
        "technical": ["scaffold", "provision", "instantiate", "bootstrap", "boilerplate", "init", "seed", "stub", "mock", "template", "code gen", "touch", "mkdir", "create-react-app", "vite", "next-app", "fastapi-gen", "docker-compose up", "terraform apply", "helm install"],
    },
    "EDIT": {
        "ancient": ["hiệu đính", "chỉnh lý", "tu bổ", "sửa đổi", "cải biên", "cập nhật", "tinh chỉnh", "tu chỉnh", "điều chỉnh", "cải thiện", "nâng cấp", "hoàn thiện", "trau chuốt", "chỉnh sửa", "bổ sung", "cải tổ", "đại tu", "sắp xếp lại"],
        "modern": ["edit", "update", "modify", "patch", "change", "refactor", "fix", "improve", "revise", "rework", "tweak", "adjust", "alter", "transform", "migrate", "upgrade", "reformat", "lint", "prettify", "beautify"],
        "slang": ["sửa hộ", "sửa dùm", "chỉnh lại", "update giúp", "fix cho tôi", "sửa giúp", "chỉnh cho đẹp", "làm lại đi", "polish đi", "mông má", "tút tát", "dọn dẹp", "tỉa tót", "vá lỗi", "đập đi xây lại"],
        "technical": ["hotfix", "performance tuning", "code optimization", "memory optimization", "restructure", "rewrite", "cleanup", "refactoring", "dependency upgrade", "code review", "formatting", "type checking", "linting", "ast manipulation", "sed replace", "git commit --amend", "git rebase"],
    },
    "DELETE": {
        "ancient": ["xóa bỏ", "triệt tiêu", "khai tử", "tiêu hủy", "loại trừ", "hủy bỏ", "xóa sạch", "bài trừ", "diệt trừ", "phá hủy", "xóa nhòa", "trừ khử", "bãi bỏ", "thu hồi", "đào thái"],
        "modern": ["delete", "remove", "erase", "clear", "destroy", "drop", "wipe", "purge", "terminate", "uninstall", "revoke", "disable", "deactivate", "retire"],
        "slang": ["ném đi", "đập bỏ", "kill", "xoá hộ", "dẹp đi", "bỏ mẹ nó đi", "cho vào sọt rác", "vứt đi", "đốt đi", "cắt béng", "thùng rác"],
        "technical": ["decommission", "cleanup", "truncate", "drop table", "garbage collect", "resource cleanup", "force delete", "hard delete", "soft delete"],
    },
    "ANALYZE": {
        "ancient": ["luận giải", "thẩm định", "giám định", "xét duyệt", "phân giải", "truy xét", "nghiên cứu", "mổ xẻ", "khảo xét", "kiểm định", "suy xét", "cân nhắc", "phân tích", "xét đoán", "quan sát", "chiêm nghiệm", "thấu thị", "dò xét"],
        "modern": ["analyze", "review", "inspect", "audit", "evaluate", "assess", "investigate", "diagnose", "debug", "examine", "breakdown", "dissect", "scrutinize", "profile", "validate", "verify", "explore", "scan", "monitor"],
        "slang": ["check giúp", "soi giúp", "xem thử", "coi thử", "bắt bệnh", "bắt lỗi", "mổ xẻ giúp", "check xem", "xem lại đi", "quét qua giúp", "ngó thử", "nhìn lướt", "đào bới", "bới lông tìm vết"],
        "technical": ["root cause analysis", "profiling", "benchmarking", "trace analysis", "system audit", "observability", "performance analysis", "static analysis", "dynamic analysis", "fuzzing", "log parsing", "telemetry inspection", "flamegraph", "memory heap dump", "ast parsing", "network sniffing"],
    },
    "EXPLAIN": {
        "ancient": ["khai sáng", "giảng giải", "minh giải", "diễn giải", "luận giải", "thuyết minh", "giải nghĩa", "khai trí", "soi đường", "chỉ bảo", "hướng dẫn", "truyền đạt"],
        "modern": ["explain", "clarify", "describe", "elaborate", "illustrate", "teach", "guide", "demonstrate", "show", "instruct", "inform", "educate", "unpack"],
        "slang": ["nói dễ hiểu", "giải thích hộ", "nói kiểu trẻ con", "explain like i'm five", "nói ngắn gọn", "eli5", "breakdown đi", "chia nhỏ ra"],
        "technical": ["documentation", "walkthrough", "deep dive", "architectural explanation", "technical explanation", "api docs", "readme", "spec"],
    },
    "PLAN": {
        "ancient": ["bày binh bố trận", "định chiến lược", "vạch lộ trình", "định hướng", "quy hoạch", "sắp đặt", "mưu tính", "phác thảo", "định kế", "sắp xếp", "bố trí", "hoạch định"],
        "modern": ["plan", "roadmap", "strategy", "workflow", "guide", "steps", "architecture", "blueprint", "outline", "scope", "sprint", "milestone", "schedule", "framework"],
        "slang": ["bày cách", "chỉ đường", "setup cho tôi", "vạch đường", "bày tôi làm", "dạy cách làm", "mô tả cách làm", "làm sao để", "làm thế nào"],
        "technical": ["system design", "distributed architecture", "multi-agent orchestration", "deployment strategy", "execution plan", "task graph", "dag planning"],
    },
    "TRANSLATE": {
        "ancient": ["phiên dịch", "chuyển ngữ", "dịch thuật", "thông ngôn", "biên dịch"],
        "modern": ["translate", "convert language", "localize", "internationalize", "dịch", "dịch sang", "dịch ra", "chuyển sang"],
        "slang": ["dịch hộ", "dịch dùm", "dịch giúp tôi", "chuyển qua tiếng", "sang tiếng"],
        "technical": ["i18n", "l10n", "locale", "language model translation", "machine translation"],
    },
}

ADVANCED_INTENT_BOOKS = {
    "DEBUG": {
        "ancient": ["truy lỗi", "bắt bệnh", "dò xét", "giám định lỗi", "khảo sát dị thường", "truy nguyên", "truy căn", "định bệnh hệ thống", "tầm tra khiếm khuyết"],
        "modern": ["debug", "fix bug", "troubleshoot", "diagnose", "repair", "resolve issue", "solve error", "hotfix", "patch", "trace error", "find bug"],
        "slang": ["vá bug", "sửa hộ", "fix dùm", "lỗi rồi", "toang rồi", "cháy rồi", "banh rồi", "die rồi", "gãy rồi", "crash", "tèo rồi", "nổ rồi", "chết rồi"],
        "technical": ["stack trace", "root cause", "exception handling", "memory leak", "race condition", "deadlock", "segmentation fault", "profiling", "telemetry"],
    },
    "SEARCH": {
        "ancient": ["truy tìm", "tầm soát", "tra cứu", "khảo sát thực địa", "truy khảo", "tầm nã thông tin", "sưu tầm", "dò la", "thăm dò"],
        "modern": ["search", "find", "lookup", "query", "scan", "google", "internet search", "web search", "tìm kiếm", "tra cứu", "lấy thông tin", "tin tức", "tín tức", "tin tuc", "tin"],
        "slang": ["tin về", "tin mới", "tình hình", "biến mới", "soi biến", "check tin", "cập nhật về", "hóng biến", "đào thông tin", "search hộ", "google giúp"],
        "technical": ["web crawling", "serp api", "real-time data acquisition", "osint", "semantic search", "vector search"],
    },
    "RESEARCH": {
        "ancient": ["thẩm cứu", "truy khảo", "khảo cứu", "nghiên cứu", "tham khảo", "luận cứu", "truy xét", "khảo sát", "điều nghiên", "tìm hiểu sâu"],
        "modern": ["research", "investigate", "study", "explore", "analyze trends", "market research", "deep research", "khám phá"],
        "slang": ["đào sâu", "soi kỹ", "tìm hiểu hộ", "đọc giúp", "research giúp", "cày về", "deep dive vào", "lặn sâu vào"],
        "technical": ["literature review", "competitive analysis", "trend analysis", "benchmark research", "state of the art", "sota"],
    },
    "SUMMARIZE": {
        "ancient": ["tổng kết", "tóm lược", "đại ý", "kết luận", "đúc kết", "khái quát", "cô đọng", "thu gọn", "lược thuật", "tinh lọc"],
        "modern": ["summarize", "summary", "brief", "tldr", "overview", "recap", "tóm tắt", "tóm lại", "tổng hợp", "rút gọn", "cô đọng", "vắn tắt"],
        "slang": ["nói ngắn gọn", "tóm lại", "brief hộ", "tổng kết hộ", "nói cho ngắn", "tóm tắt hộ", "dài quá tóm lại đi", "ngắn thôi"],
        "technical": ["executive summary", "abstract", "compressed reasoning", "key takeaways", "highlight", "digest"],
    },
}

# ==========================================
# 2. MIỀN TRI THỨC & SẮP XẾP CÔNG CỤ
# ==========================================

TOOL_ROUTING_BOOK = {
    "WEB_SEARCH": ["latest", "news", "search web", "google", "internet", "online", "tin tuc", "bao chi", "cap nhat", "thong tin moi", "tim kiem", "tra cuu", "tin về", "tình hình", "bài báo"],
    "CODE_EXECUTION": ["run code", "execute", "python", "benchmark", "calculate", "chạy code", "thực thi"],
    "TERMINAL": ["shell", "bash", "cmd", "terminal", "powershell", "dòng lệnh"],
}

DOMAIN_BOOKS = {
    "AI_AGENT": ["agentic", "multi-agent", "orchestrator", "dispatcher", "planner", "critic", "reflection", "memory", "retrieval", "rag", "embedding", "rerank", "reasoning", "thinking", "tool calling", "knowledge graph", "autonomous ai", "llm", "prompt engineering", "langchain", "llamaindex", "qdrant", "chroma", "vector store", "semantic search", "fine-tuning", "lora", "transformers", "openai", "anthropic", "gemini", "claude"],
    "CODING": ["python", "javascript", "typescript", "golang", "rust", "java", "c#", "api", "backend", "frontend", "fullstack", "docker", "kubernetes", "redis", "postgres", "mongodb", "fastapi", "nestjs", "react", "vue", "nextjs", "svelte", "angular", "django", "flask", "spring boot", "express", "graphql", "rest", "grpc", "websocket", "html", "css", "tailwind", "bootstrap", "sass", "webpack", "vite", "babel", "npm", "yarn", "pnpm", "pip", "poetry", "cargo", "nuget", "maven", "gradle", "git", "github", "gitlab", "bitbucket", "vscode", "intellij", "pycharm", "webstorm", "neovim", "vim", "emacs", "jupyter"],
    "DEVOPS": ["deployment", "terraform", "ansible", "nginx", "traefik", "cloudflare", "ci/cd", "pipeline", "scaling", "load balancing", "monitoring", "grafana", "prometheus", "aws", "gcp", "azure", "kubernetes", "k8s", "docker swarm", "helm", "argocd", "jenkins", "github actions", "gitlab ci", "circleci", "travisci", "datadog", "new relic", "sentry", "elk", "elastic search", "logstash", "kibana", "fluentd", "splunk", "pagerduty", "opsgenie", "infrastructure as code", "iac", "serverless", "lambda", "cloud run", "fargate", "ecs", "eks", "aks", "gke"],
    "SECURITY": ["xss", "csrf", "sql injection", "exploit", "vulnerability", "pentest", "authentication", "authorization", "sandbox", "rbac", "zero trust", "oauth", "jwt", "saml", "sso", "mfa", "2fa", "encryption", "decryption", "hashing", "salt", "bcrypt", "argon2", "pbkdf2", "ssl", "tls", "https", "certificate", "public key", "private key", "rsa", "ecc", "aes", "des", "firewall", "waf", "ids", "ips", "siem", "soc", "phishing", "malware", "ransomware", "ddos", "botnet", "mitm", "owasp", "cve", "cvss"],
    "DATA": ["dataset", "csv", "excel", "json", "xml", "etl", "analytics", "chart", "dashboard", "dataframe", "visualization", "pandas", "numpy", "scipy", "scikit-learn", "tensorflow", "pytorch", "keras", "matplotlib", "seaborn", "plotly", "bokeh", "d3", "tableau", "powerbi", "looker", "metabase", "superset", "snowflake", "redshift", "bigquery", "databricks", "spark", "hadoop", "kafka", "flink", "storm", "airflow", "luigi", "prefect", "dbt", "sql", "nosql", "graphdb", "neo4j", "arangodb", "cassandra", "hbase", "dynamodb", "cosmosdb"],
    "NEWS": ["tin tức", "báo chí", "thời sự", "thế giới", "trong nước", "hôm nay", "hôm qua", "ngày mai", "tuần này", "tháng này", "sự kiện", "cập nhật", "nóng", "hot", "xu hướng", "trend", "breaking news", "chính trị", "xã hội", "kinh tế", "văn hóa", "thể thao", "giải trí", "khoa học", "công nghệ", "giáo dục", "pháp luật", "đời sống", "sức khỏe", "thế giới động vật", "khám phá", "bí ẩn"],
    "SYSTEM": ["hệ thống", "system", "os", "máy chủ", "máy tính", "chuỗi", "tiến trình", "quy trình", "pipeline", "lệnh", "terminal", "bash", "shell", "powershell", "cmd", "linux", "windows", "macos", "ubuntu", "centos", "debian", "alpine", "arch", "fedora", "redhat", "suse", "kernel", "cpu", "ram", "disk", "storage", "network", "ip", "mac address", "port", "socket", "tcp", "udp", "http", "https", "ftp", "ssh", "telnet", "dns", "dhcp", "ping", "traceroute", "curl", "wget", "netstat", "ifconfig", "ipconfig", "nmap"],
    "MEMORY": ["bộ nhớ", "ký ức", "bộ não", "memory", "cache", "redis", "qdrant", "database", "dữ liệu", "lịch sử", "ngữ cảnh", "bối cảnh", "context", "history", "log", "trace", "session", "cookie", "local storage", "session storage", "indexeddb", "sqlite", "mysql", "mariadb", "oracle", "sql server", "memcached", "etcd", "zookeeper", "consul"],
}

# ==========================================
# 3. GHÉP CẶP Ý ĐỊNH HOẠT ĐỘNG VÀ BỐI CẢNH
# ==========================================

ACTION_PAIR_BOOK = {
    "SEARCH": [
        ("tìm", "tin tức"), ("tìm kiếm", "thông tin"), ("tra cứu", "bài báo"), ("tìm", "bài viết"), ("lấy", "tin"), ("cập nhật", "tin"),
        ("search", "news"), ("find", "articles"), ("hóng", "biến"), ("xem", "tình hình"), ("lấy", "thông tin"), ("tìm", "dữ liệu"), ("thu thập", "tin tức"),
        ("quét", "mạng"), ("dò", "kết quả"), ("lục", "tìm"), ("bới", "thông tin"), ("truy xuất", "dữ liệu"), ("fetch", "data"), ("get", "info")
    ],
    "SUMMARIZE": [
        ("tóm tắt", "bài viết"), ("tổng hợp", "tin tức"), ("rút gọn", "nội dung"), ("tóm lại", "đoạn văn"), ("tóm tắt", "tài liệu"), ("đúc kết", "ý chính"), ("điểm lại", "nội dung"), ("brief", "document"),
        ("tổng", "kết"), ("khái", "quát"), ("rút", "cốt lõi"), ("cô đọng", "thông tin"), ("lược", "dịch")
    ],
    "CREATE": [
        ("viết", "bài"), ("tạo", "nội dung"), ("soạn", "thảo"), ("generate", "report"), ("viết", "email"), ("tạo", "báo cáo"), ("soạn", "bài viết"), ("viết", "code"), ("tạo", "script"), ("làm", "template"),
        ("xây", "dựng"), ("lập", "trình"), ("thiết", "kế"), ("phát", "triển"), ("dựng", "app"), ("code", "chức năng"), ("build", "project"), ("setup", "môi trường")
    ],
    "DEBUG": [
        ("sửa", "lỗi"), ("fix", "bug"), ("bắt", "lỗi"), ("tìm", "bug"), ("vá", "lỗi"), ("resolve", "error"), ("khắc phục", "sự cố"), ("trace", "exception"),
        ("gỡ", "rối"), ("chữa", "cháy"), ("cứu", "net"), ("debug", "code"), ("xử lý", "lỗi"), ("sửa", "code"), ("chỉnh", "bug")
    ],
    "ANALYZE": [
        ("phân tích", "dữ liệu"), ("đánh giá", "tình hình"), ("đọc", "file"), ("kiểm tra", "mã nguồn"), ("phân tích", "log"), ("xem", "code"),
        ("soi", "code"), ("review", "code"), ("audit", "hệ thống"), ("giám định", "chất lượng"), ("thẩm định", "kết quả"), ("mổ xẻ", "vấn đề")
    ],
    "PLAN": [
        ("lập", "kế hoạch"), ("vạch", "chiến lược"), ("lên", "phương án"), ("tạo", "workflow"), ("thiết kế", "hệ thống"),
        ("chia", "bước"), ("định", "hướng"), ("vẽ", "lộ trình"), ("phác thảo", "ý tưởng"), ("brainstorm", "giải pháp")
    ],
}

CONTEXT_PAIR_BOOK = {
    "TIME_LOCATION": [
        ("thế giới", "hôm nay"), ("toàn cầu", "hiện tại"), ("việt nam", "hôm qua"), ("trong nước", "tuần này"), ("mỹ", "hôm nay"), ("châu á", "gần đây"), ("toàn cầu", "mới đây"), ("quốc tế", "hiện tại")
    ],
    "TOPIC_TIME": [
        ("công nghệ", "hôm nay"), ("kinh tế", "tuần này"), ("thể thao", "hôm qua"), ("chính trị", "gần đây"), ("sức khỏe", "mới đây"), ("ai", "tuần này"), ("crypto", "hôm nay"), ("giáo dục", "tháng này"),
        ("chứng khoán", "dạo này"), ("thị trường", "hiện tại"), ("cổ phiếu", "dạo này"), ("tình hình", "dạo này")
    ],
}

# ==========================================
# 4. CHIỀU NHẬN THỨC BỔ SUNG (DIMENSIONS)
# ==========================================

POLITENESS_BOOK = {
    "FORMAL": ["kính gửi", "xin trân trọng", "xin phép", "kính thưa", "trân trọng", "thưa", "kính mong", "xin hỏi"],
    "INFORMAL": ["ôi", "ơi", "bạn ơi", "bro", "này", "anh ơi", "chị ơi", "hey bro", "ê"],
    "COMMANDING": ["làm ngay", "làm đi", "làm liền", "phải", "cần phải", "bắt buộc", "ngay lập tức", "run it", "just do it"],
    "REQUESTING": ["giúp tôi", "giúp mình", "cho tôi", "cho mình", "bạn có thể", "có thể giúp", "làm ơn", "vui lòng", "please", "kindly"],
}

QUESTION_TYPE_BOOK = {
    "WHAT": ["là gì", "what is", "định nghĩa", "khái niệm", "ý nghĩa của", "là như thế nào"],
    "HOW": ["làm thế nào", "bằng cách nào", "như thế nào", "how to", "cách để", "cách làm"],
    "WHY": ["tại sao", "vì sao", "lý do", "nguyên nhân", "why", "sao lại"],
    "WHEN": ["khi nào", "bao giờ", "thời điểm", "when", "when is"],
    "WHERE": ["ở đâu", "nơi nào", "chỗ nào", "where", "where is"],
}

CONTENT_FORMAT_BOOK = {
    "LIST": ["liệt kê", "danh sách", "list", "bullet points", "gạch đầu dòng", "các bước", "enumerate"],
    "TABLE": ["bảng", "table", "dạng bảng", "so sánh dạng bảng", "tabular"],
    "CODE": ["code", "đoạn code", "script", "snippet", "implement", "viết code"],
    "JSON": ["json", "json format", "dạng json", "trả về json"],
}

USER_PERSONA_BOOK = {
    "DEVELOPER": ["developer", "lập trình viên", "dev", "coder", "programmer", "kỹ sư phần mềm"],
    "MANAGER": ["manager", "quản lý", "pm", "product manager", "trưởng nhóm", "team lead"],
}

META_BOOKS = {
    "CONTINUE": ["tiếp tục", "go on", "continue", "tiếp theo", "tiếp"],
    "RETRY": ["thử lại", "retry", "redo", "làm lại"],
    "CONFIRM": ["ok", "oke", "đồng ý", "xác nhận", "confirm", "được", "chắc chắn"],
    "REJECT": ["không đúng", "sai rồi", "reject", "no", "không phải"],
    "STOP": ["dừng lại", "stop", "dừng", "ngừng", "thôi", "hủy lệnh", "đừng làm nữa"],
    "ABORT": ["hủy bỏ", "abort", "thoát", "cancel", "tắt"],
}

SOCIAL_EMOTION_BOOKS = {
    "CONFUSED": ["không hiểu", "rối", "confused", "khó hiểu", "wtf", "hả", "sao", "lú", "ngáo", "chịu", "hại não", "lùng bùng", "chằm zn", "ố dề", "ảo ma", "ảo ma canada", "bất ổn", "cảm lạnh", "chịu thua", "xà lơ"],
    "FRUSTRATED": ["bực", "ức chế", "annoying", "điên rồi", "stress", "mệt", "tức giận", "bực tức", "tức tối", "cáu", "nản", "chán", "trầm cảm", "vl", "vãi", "chết tiệt", "đm", "vcl", "xu cà na", "ét o ét", "hết cứu", "tới công chuyện", "bó tay", "toang", "đứt"],
    "EXCITED": ["quá hay", "đỉnh", "awesome", "amazing", "ngon", "xịn", "tuyệt", "đỉnh cao", "vip", "pro", "10 điểm", "cháy", "chất", "bá đạo", "ảo thật", "mãi đỉnh", "đỉnh chóp", "đỉnh của chóp", "keo", "mận", "đét", "quá đã"],
    "GREETING": ["chào", "hello", "hi", "hey", "khỏe không", "cảm ơn", "thanks", "thank you", "xin chào", "chào buổi sáng", "good morning", "chào buổi tối", "good evening", "aloo", "alo", "có ai không", "hé lô", "hế lô", "hi ya", "bạn thế nào", "thế nào rồi", "dạo này thế nào", "sao rồi", "như thế nào rồi"],
    "PRAISE": ["giỏi", "thông minh", "tốt lắm", "good job", "xuất sắc", "đỉnh kout", "rất tốt", "làm tốt lắm", "mãi yêu", "yêu luôn", "chất lừ", "chuẩn không cần chỉnh", "quá xịn"],
    "DISAPPOINTED": ["tệ", "chán", "dở", "sai bét", "stupid", "ngu", "kém", "chả ra gì", "thất vọng", "không ưng", "quá tệ", "trớt", "fail", "cùi", "lởm"],
}

COGNITIVE_SIGNALS = {
    "THINKING": ["suy nghĩ", "think", "reason", "lập luận", "cân nhắc", "phân tích logic", "ngẫm"],
    "BRAINSTORM": ["brainstorm", "ý tưởng", "gợi ý", "idea", "concept", "động não"],
}

PRIORITY_BOOK = {
    "CRITICAL": ["khẩn cấp", "urgent", "critical", "ngay lập tức", "asap", "gấp", "sập rồi"],
    "HIGH": ["quan trọng", "important", "ưu tiên", "priority", "cần nhanh"],
}

EXECUTION_STYLE = {
    "FAST": ["nhanh", "quick", "fast", "brief", "tóm gọn", "nhanh thôi"],
    "DETAILED": ["chi tiết", "detailed", "deep dive", "kỹ càng", "đầy đủ"],
}

# NEW: Bổ sung ngữ cảnh Phủ định nâng cao để cắt giảm nhiễu thông tin mẫu
NEGATION_BOOK = {
    "NEGATION": ["không", "đừng", "chưa", "chẳng", "chả", "không được", "ngưng", "thôi", "cấm", "bỏ qua"]
}

# NEW: Bổ sung nhận diện Ngôn ngữ Đầu vào (Language Identification)
LANGUAGE_INDICATORS = {
    "VIETNAMESE": ["không", "người", "tôi", "làm", "sửa", "chạy", "gì", "báo_cáo", "lỗi", "tóm_tắt"],
    "ENGLISH": ["the", "and", "please", "with", "from", "create", "delete", "issue", "how", "what"]
}

MULTI_LANG_ALIAS = {
    " ko ": " không ", " k ": " không ", " hok ": " không ", " kh ": " không ", " kg ": " không ", " đéo ": " không ", " chả ": " không ", " khum ": " không ", " hông ": " không ", 
    " dc ": " được ", " đc ": " được ", " oki ": " ok ", " okie ": " ok ", " uk ": " ừ ", " uh ": " ừ ", " um ": " ừ ", " ukm ": " ừ ", " u ": " ừ ",
    " j ": " gì ", " mik ": " mình ", " mk ": " mình ", " bn ": " bạn ", " b ": " bạn ", " m ": " mày ", " t ": " tao ", " tui ": " tôi ",
    " bh ": " bao giờ ", " bao h ": " bao giờ ", " bjo ": " bao giờ ", " r ": " rồi ", " thui ": " thôi ", " cx ": " cũng ", " xog ": " xong ", " ch ": " chưa ",
    " ntn ": " như thế nào ", " s ": " sao ", " v ": " vậy ", " z ": " vậy ", " zj ": " vậy ", " zị ": " vậy ", " vs ": " với ", " vs ": " versus ",
    " ae ": " anh em ", " mn ": " mọi người ", " fen ": " bạn ", " bro ": " bạn ", " pro ": " chuyên nghiệp ", " gơ ": " girl ", " zai ": " trai ",
    " pls ": " please ", " plz ": " please ", " asap ": " urgent ", " btw ": " by the way ", " idk ": " i dont know ", " fyi ": " for your information ", " lmfao ": " haha ", " lmao ": " haha ", " lol ": " haha ",
    " ht ": " hiện tại ", " tl ": " trả lời ", " rep ": " trả lời ", " ib ": " inbox ", " cmt ": " comment ", " inb ": " inbox ", " onl ": " online ", " off ": " offline ",
    " sp ": " sản phẩm ", " sv ": " server ", " db ": " database ", " fe ": " frontend ", " be ": " backend ", " fs ": " fullstack ",
    " rag ": " retrieval augmented generation ", " cot ": " chain of thought ", " tot ": " tree of thought ", " moe ": " mixture of experts ", " llm ": " large language model ",
    " k8s ": " kubernetes ", " tf ": " terraform ", " gh ": " github ", " wip ": " work in progress ", " pr ": " pull request ", " mr ": " merge request ",
    " oke ": " ok ", " thoy ": " thôi ", " dùm ": " giúp ", " giùm ": " giúp ", " nha ": " nhé ", " nhe ": " nhé ", " ha ": " hả ", " ms ": " mới ", " ùi ": " rồi "
}

CONTEXT_BOOKS = {
    "TIME": {
        "today": ["hôm nay", "ngày hôm nay", "hiện tại", "bây giờ", "today", "ngay bây giờ"],
        "yesterday": ["hôm qua", "ngày hôm qua", "yesterday"],
        "tomorrow": ["ngày mai", "tomorrow"],
        "recent": ["mới đây", "gần đây", "dạo này", "dạo gần đây", "recent", "latest", "mới nhất", "vừa xong", "cập nhật", "này"],
    },
    "LOCATION": {
        "global": ["thế giới", "toàn cầu", "quốc tế", "global", "international"],
        "vietnam": ["việt nam", "trong nước", "vn", "vietnam"],
        "usa": ["mỹ", "hoa kỳ", "usa"],
    },
    "TOPIC": {
        "technology": ["công nghệ", "tech", "it"],
        "economy": ["kinh tế", "economy", "tài chính", "chứng khoán", "cổ phiếu", "crypto", "thị trường"],
        "ai_news": ["trí tuệ nhân tạo", "ai", "chatgpt", "tin ai"],
    }
}

# ==========================================
# 5. BỘ ĐIỀU TỐC VÀ XỬ LÝ (THE ENGINE OPTIMIZED)
# ==========================================

# Cải tiến: Thêm dấu câu vào normalize để regex ranh giới từ `\b` hoạt động trơn tru hơn
def _normalize(goal: str) -> str:
    if not goal:
        return ""
    patterns = {
        '[àáảãạăằắẳẵặâầấẩẫậ]': 'a', '[èéẻẽẹêềếểễệ]': 'e', '[ìíỉĩị]': 'i',
        '[òóỏõọôồốổỗộơờớởỡợ]': 'o', '[ùúủũụưừứửữự]': 'u', '[ỳýỷỹỵ]': 'y', '[đ]': 'd'
    }
    # Loại bỏ các ký tự dấu câu cơ bản để tránh block text bị phân tách sai lệch
    clean = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()!?]', ' ', goal.lower())
    clean = " " + " ".join(clean.split()) + " "
    
    for slang, correct in MULTI_LANG_ALIAS.items():
        clean = clean.replace(slang, f" {correct.strip()} ")
        
    return " ".join(clean.split())

def _build_layer(*books) -> list:
    combined_flat = {}
    for book in books:
        for intent, categories in book.items():
            words_list = []
            if isinstance(categories, dict):
                for words in categories.values(): 
                    words_list.extend(words)
            else: 
                words_list = categories
                
            for w in words_list:
                w_lower = w.lower()
                combined_flat[w_lower] = intent
                norm_w = _normalize(w_lower)
                if norm_w != w_lower and norm_w: 
                    combined_flat[norm_w] = intent
                    
    # Sắp xếp các từ khóa theo chiều dài giảm dần nhằm khớp từ dài nhất trước (Ví dụ: "hệ thống" trước "hệ")
    sorted_keys = sorted(combined_flat.keys(), key=len, reverse=True)
    return [
        (kw, combined_flat[kw], re.compile(rf'\b{re.escape(kw)}\b'), re.compile(rf'\b{re.escape(kw)}')) 
        for kw in sorted_keys if kw.strip()
    ]

def _classify_layer(clean_goal: str, compiled_patterns: list) -> dict:
    scores = {}
    for kw, intent, reg_full, reg_start in compiled_patterns:
        current_max = scores.get(intent, 0.0)
        if current_max >= 1.0: 
            continue
            
        if reg_full.search(clean_goal): 
            score = 1.0
        elif reg_start.search(clean_goal) and len(kw) >= 3: 
            score = 0.8
        elif kw in clean_goal and len(kw) >= 4: 
            score = 0.5
        else: 
            continue
            
        if score > current_max: 
            scores[intent] = score
            
    if not scores: 
        return {"value": None, "confidence": 0.0, "candidates": []}
        
    sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "value": sorted_candidates[0][0], 
        "confidence": sorted_candidates[0][1], 
        "candidates": sorted_candidates[:3]
    }

# ==========================================
# 6. CÁC HÀM TRÍCH XUẤT THÔNG TIN THỰC THỂ
# ==========================================

def extract_action_pairs(clean_goal: str) -> List[Tuple[str, str, str]]:
    pairs = []
    for intent, pair_list in ACTION_PAIR_BOOK.items():
        for (act, obj) in pair_list:
            norm_act = _normalize(act)
            norm_obj = _normalize(obj)
            if norm_act in clean_goal and norm_obj in clean_goal:
                pairs.append((intent, act, obj))
    return list(set(pairs))

def extract_context_pairs(clean_goal: str) -> List[Tuple[str, str, str]]:
    pairs = []
    for intent, pair_list in CONTEXT_PAIR_BOOK.items():
        for (val1, val2) in pair_list:
            norm_v1 = _normalize(val1)
            norm_v2 = _normalize(val2)
            if norm_v1 in clean_goal and norm_v2 in clean_goal:
                pairs.append((intent, val1, val2))
    return list(set(pairs))

def extract_scalar(clean_goal: str) -> Optional[int]:
    numbers = re.findall(r'\b(\d+)\b', clean_goal)
    return int(numbers[0]) if numbers else None

def extract_entities(clean_goal: str) -> Dict[str, List[str]]:
    result = {"time": [], "location": [], "topic": []}
    for cat, subcat in CONTEXT_BOOKS.items():
        for key, words in subcat.items():
            for w in words:
                if _normalize(w) in clean_goal: 
                    result[cat.lower()].append(key)
    for k in result: 
        result[k] = list(set(result[k]))
    return result

# Compile toàn bộ Layer tĩnh một lần duy nhất lúc khởi chạy hệ thống
_L_TASK      = _build_layer(INTENT_BOOKS, ADVANCED_INTENT_BOOKS)
_L_DOMAIN    = _build_layer(DOMAIN_BOOKS)
_L_POLITE    = _build_layer(POLITENESS_BOOK)
_L_QTYPE     = _build_layer(QUESTION_TYPE_BOOK)
_L_FORMAT    = _build_layer(CONTENT_FORMAT_BOOK)
_L_PERSONA   = _build_layer(USER_PERSONA_BOOK)
_L_NEGATION  = _build_layer(NEGATION_BOOK)
_L_SOCIAL    = _build_layer(SOCIAL_EMOTION_BOOKS)
_L_COGNITIVE = _build_layer(COGNITIVE_SIGNALS)
_L_PRIORITY  = _build_layer(PRIORITY_BOOK)
_L_STYLE     = _build_layer(EXECUTION_STYLE)
_L_META      = _build_layer(META_BOOKS)
_L_LANG      = _build_layer(LANGUAGE_INDICATORS)

# ==========================================
# 7. HÀM PHÂN TÍCH TỔNG LỰC CHÍNH (MASTER SOVEREIGN)
# ==========================================

@lru_cache(maxsize=1024) # Tăng kích thước bộ nhớ Cache lên 1024
def full_classify(goal: str) -> dict:
    """📊 Radar 14D Sovereign: Phân tích đa chiều ý định Master đã được nâng cấp."""
    if not goal or not goal.strip():
        return {"task": {"value": None, "confidence": 0.0, "candidates": []}}

    clean = _normalize(goal)
    
    # 1. Trích xuất cơ bản thông qua khớp Layer từ vựng định sẵn
    task_res = _classify_layer(clean, _L_TASK)
    neg_res = _classify_layer(clean, _L_NEGATION)
    lang_res = _classify_layer(clean, _L_LANG)
    
    # 2. XỬ LÝ LOGIC PHỦ ĐỊNH (Cải tiến quan trọng)
    # Nếu câu chứa cụm từ phủ định đứng trước intent, ta hạ mức độ tin cậy của intent đó xuống.
    if neg_res["value"] is not None and task_res["value"] is not None:
        task_res["confidence"] *= 0.2  # Giảm trọng số tin cậy do dính phủ định
        
    return {
        "task": task_res,
        "social": _classify_layer(clean, _L_SOCIAL),
        "domain": _classify_layer(clean, _L_DOMAIN),
        "politeness": _classify_layer(clean, _L_POLITE),
        "question_type": _classify_layer(clean, _L_QTYPE),
        "format": _classify_layer(clean, _L_FORMAT),
        "persona": _classify_layer(clean, _L_PERSONA),
        "negation": neg_res,
        "cognitive": _classify_layer(clean, _L_COGNITIVE),
        "priority": _classify_layer(clean, _L_PRIORITY),
        "style": _classify_layer(clean, _L_STYLE),
        "meta": _classify_layer(clean, _L_META),
        "language": lang_res["value"] if lang_res["value"] else "UNDETERMINED",
        "action_pairs": extract_action_pairs(clean),
        "context_pairs": extract_context_pairs(clean),
        "scalar": extract_scalar(clean),
        "entities": extract_entities(clean),
        "is_question": goal.strip().endswith('?') or _classify_layer(clean, _L_QTYPE)["value"] is not None
    }

def get_role_lexicon(role: str) -> str:
    role = role.upper()
    lexicon_parts = [f"--- [{role} SOVEREIGN LEXICON] ---"]
    if role == "RECEPTIONIST":
        lexicon_parts.append(f"ACTION_PAIRS: {json.dumps(ACTION_PAIR_BOOK, ensure_ascii=False)}")
        lexicon_parts.append(f"CONTEXT_PAIRS: {json.dumps(CONTEXT_PAIR_BOOK, ensure_ascii=False)}")
        lexicon_parts.append(f"SOCIAL_EMOTION: {json.dumps(SOCIAL_EMOTION_BOOKS, ensure_ascii=False)}")
    return "\n".join(lexicon_parts)
