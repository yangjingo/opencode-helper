# 验证流程优化设计文档

**日期:** 2026-07-15  
**主题:** OpenCode Helper 验证流程优化  
**方案:** 混合方案 (C)

---

## 1. 背景与问题

当前验证流程存在以下问题：

1. **串行执行** - 4个测试依次运行，总耗时 = API测试 + 模型测试 + CLI测试 + 配置检查
2. **无重试机制** - 网络抖动导致偶发失败，用户需手动重试
3. **错误信息不足** - 无法快速定位是网络问题、认证问题还是配置问题
4. **固定超时** - 不同 provider 需要不同的超时策略（阿里 Coding Plan 响应更快）
5. **无进度粒度** - 用户看不到当前进行到哪一步
6. **硬编码模型** - `test_endpoint` 使用 `claude-sonnet-5` 而非用户配置的模型
7. **无 provider 差异化** - 所有 provider 使用相同的测试逻辑
8. **无诊断建议** - 部分失败时（如 API 通但 CLI 失败），没有下一步指引

---

## 2. 设计目标

| 目标 | 指标 |
|------|------|
| 速度 | 并行执行后总耗时 <= 最慢单个测试的耗时 |
| 稳定性 | 网络抖动场景下成功率 >= 95% |
| 体验 | 用户能看到实时进度和详细错误原因 |
| 智能 | 自动识别 provider 并使用最优测试策略 |

---

## 3. 架构设计

### 3.1 模块结构

```
src/core/
├── providers.py          # 新增：provider 配置和策略
├── validation_engine.py  # 新增：并行调度引擎
├── validator.py          # 重构：策略化的验证函数
└── validation_result.py  # 新增：统一结果结构

src/ui/pages/
└── verify.py             # 增强：细粒度进度 + 诊断建议
```

### 3.2 核心组件

#### Provider 配置 (`providers.py`)

```python
PROVIDER_CONFIG = {
    'dashscope': {
        'name': 'Alibaba Coding Plan',
        'test_strategy': 'direct_post',  # 直接POST到baseURL
        'timeout': (5, 15),  # (连接超时, 读取超时)
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {'anthropic-version': '2023-06-01'},
        'default_test_model': 'qwen3.7-plus',  # 用户未配置模型时的默认测试模型
        'available_models': [  # 用于错误提示时显示可用模型
            'qwen3.7-plus', 'qwen3.6-plus', 'qwen3.5-plus',
            'qwen3-max-2026-01-23', 'qwen3-coder-next', 'qwen3-coder-plus',
            'MiniMax-M2.5', 'glm-5', 'glm-4.7', 'kimi-k2.5'
        ],
    },
    'deepseek': {
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'deepseek-chat',
        'available_models': ['deepseek-chat', 'deepseek-reasoner'],
    },
    'openai': {
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'default_test_model': 'gpt-4o',
        'available_models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    },
    'anthropic': {
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'default_test_model': 'claude-sonnet-4',
        'available_models': ['claude-opus-4', 'claude-sonnet-4', 'claude-haiku-4'],
    },
    'default': {
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'default_test_model': 'claude-sonnet-4',
    }
}

def get_provider_config(base_url: str) -> dict:
    """根据 base_url 返回 provider 配置"""
    
def resolve_test_model(provider_config: dict, user_model_id: str) -> str:
    """
    确定测试使用的模型 ID。
    
    优先级:
    1. 用户配置的 model_id (如果非空且有效)
    2. provider 配置的 default_test_model
    
    使用用户配置的 model_id 更真实，但如果为空或无效，
    则使用 provider 默认模型确保测试能执行。
    """
```

#### 验证引擎 (`validation_engine.py`)

```python
class ValidationEngine:
    """
    并行执行验证任务，支持细粒度进度回调。
    
    Usage:
        engine = ValidationEngine(state)
        engine.on_progress = lambda msg, progress: ui.update(msg, progress)
        results = engine.run_all()
    """
    
    def __init__(self, state: WizardState):
        self.state = state
        self.provider_config = get_provider_config(state.base_url)
        self.on_progress: Callable[[str, float], None] = None
    
    def run_all(self) -> ValidationReport:
        """并行执行所有验证，返回完整报告"""
        tasks = [
            ('endpoint', self._test_endpoint),
            ('model', self._test_model),
            ('cli', self._test_cli),
            ('config', self._test_config),
        ]
        # ThreadPoolExecutor 并行执行
        # 每个任务有独立重试逻辑
        # 进度回调: 0.0 -> 0.25 -> 0.5 -> 0.75 -> 1.0
    
    def _test_endpoint(self) -> ValidationResult:
        """根据 provider_config['test_strategy'] 选择测试方式"""
```

#### 统一结果结构 (`validation_result.py`)

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class Status(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    WARNING = 'warning'  # 部分成功

@dataclass
class ValidationResult:
    name: str                    # 测试名称
    status: Status               # 状态
    duration_ms: int             # 执行耗时
    message: str                 # 简短描述
    detail: Optional[str]        # 详细错误信息
    suggestion: Optional[str]    # 用户操作建议
    metadata: Dict[str, Any]     # 额外数据（如 status_code）
    
    @property
    def ok(self) -> bool:
        return self.status in (Status.SUCCESS, Status.WARNING)

@dataclass  
class ValidationReport:
    results: List[ValidationResult]
    total_duration_ms: int
    overall_status: Status
    
    def get_failed(self) -> List[ValidationResult]:
        return [r for r in self.results if r.status == Status.FAILED]
    
    def get_suggestions(self) -> List[str]:
        """返回所有失败的建议操作"""
```

#### 策略化验证 (`validator.py`)

**模型 ID 选择策略:**

测试模型推理时，按以下优先级选择 model_id：

1. **用户配置的 model_id** — 如果非空，优先使用（最真实地验证用户配置）
2. **Provider 默认测试模型** — 如果用户未配置，使用 `provider_config['default_test_model']`

这样既能验证用户真实配置，又能确保测试不会因空 model_id 而失败。

```python
# 策略注册表
TEST_STRATEGIES = {}

def register_strategy(name: str):
    def decorator(func):
        TEST_STRATEGIES[name] = func
        return func
    return decorator

@register_strategy('direct_post')
def test_direct_post(base_url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """直接POST到baseURL，不追加任何路径
    
    model_id: 优先使用用户配置，如为空则使用 config['default_test_model']
    """
    actual_model = model_id or config.get('default_test_model', 'unknown')
    # 使用 actual_model 进行测试
    
@register_strategy('openai_compatible')
def test_openai_compatible(base_url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """OpenAI 兼容格式: /v1/chat/completions"""
    actual_model = model_id or config.get('default_test_model', 'gpt-4o')
    
@register_strategy('anthropic_compatible')
def test_anthropic_compatible(base_url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """Anthropic 兼容格式: /v1/messages"""
    actual_model = model_id or config.get('default_test_model', 'claude-sonnet-4')

# 带重试的包装器
def with_retry(config: dict):
    def decorator(func):
        def wrapper(*args, **kwargs) -> ValidationResult:
            for attempt in range(config['retry']['times']):
                result = func(*args, **kwargs)
                if result.ok or attempt == config['retry']['times'] - 1:
                    return result
                time.sleep(config['retry']['backoff'] * (2 ** attempt))
        return wrapper
    return decorator
```

### 3.3 UI 增强 (`verify.py`)

#### 进度展示

```python
class VerifyPage(BasePage):
    def __init__(self, ...):
        # 添加进度条
        self.progress = ttk.Progressbar(..., mode='determinate')
        self.status_labels = {}  # 每个测试的状态标签
        
    def _run_tests(self):
        def on_progress(name: str, value: float):
            # 更新进度条和状态标签
            self.progress['value'] = value * 100
            self.status_labels[name].configure(
                text=f'⏳ {name}...',
                fg=COLORS['yellow']
            )
        
        engine = ValidationEngine(self.app.state)
        engine.on_progress = on_progress
        report = engine.run_all()
        self._show_report(report)
    
    def _show_report(self, report: ValidationReport):
        # 显示结果 + 诊断建议
        for result in report.results:
            icon = '✓' if result.ok else '✗'
            color = COLORS['neon_green'] if result.ok else COLORS['red']
            
            # 显示建议
            if result.suggestion:
                self._add_suggestion_box(result.suggestion)
```

#### 诊断建议矩阵

| 失败场景 | 建议操作 |
|---------|---------|
| Endpoint 401 | "API Key 无效，请检查 ~/.config/opencode/opencode.jsonc 中的 apiKey" |
| Endpoint 404 | "Endpoint 地址错误，Coding Plan 应使用: https://coding.dashscope.aliyuncs.com/apps/anthropic/v1" |
| Endpoint 超时 | "网络连接失败，检查代理设置或尝试关闭 VPN" |
| Model 失败但 Endpoint 成功 | "模型 ID 错误，可用模型: qwen3.7-plus, qwen3.6-plus..." |
| CLI 未找到 | "OpenCode 未安装，点击返回重新安装" |
| CLI 配置错误 | "运行 'opencode doctor' 检查配置" |

---

## 4. 执行顺序

```
Phase 1: 基础结构
├── validation_result.py   # 定义数据结构
├── providers.py           # provider 配置
└── validation_engine.py    # 引擎框架

Phase 2: 策略实现
└── validator.py           # 迁移 + 策略化

Phase 3: UI 集成
└── verify.py              # 增强进度和诊断

Phase 4: 测试
└── 手动测试各 provider
```

---

## 5. 兼容性

- **API 兼容:** 保持 `run_all()` 函数签名不变，返回结果增加字段
- **UI 兼容:** 保留现有终端风格，仅添加进度元素
- **配置兼容:** 不改变 opencode.jsonc 格式

---

## 6. 风险评估

| 风险 | 缓解措施 |
|------|---------|
| 并行导致线程安全问题 | 每个测试独立运行，不共享可变状态 |
| 进度回调阻塞 UI | 使用 `after()` 调度 UI 更新 |
| 超时策略不当 | 提供合理的默认值，用户可在配置中覆盖 |

---

## 7. 成功标准

- [ ] API + Model + CLI + Config 并行执行，总耗时 <= 单个最慢测试
- [ ] 网络抖动场景（模拟丢包）成功率 >= 95%
- [ ] 用户能看到实时进度百分比
- [ ] 失败时显示具体建议和修复步骤
- [ ] 支持阿里 Coding Plan / DeepSeek / OpenAI / Anthropic 的差异化测试

---

**作者:** Claude  
**状态:** 待审查
