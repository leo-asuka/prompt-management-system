# src/app/llm_client.py

from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from jinja2 import Template  # 使用 Jinja2 来做模板替换
from .config import settings

# 1. 初始化 OpenAI 客户端
# 客户端在模块加载时被实例化一次，这是一种高效的单例模式
try:
    # client = OpenAI(
    #     api_key=settings.OPENAI_API_KEY,
    #     timeout=20.0,  # 设置默认超时时间
    # )
    client = OpenAI(
        # defaults to os.environ.get("OPENAI_API_KEY")
        api_key=settings.OPENAI_API_KEY,
        base_url="https://api.chatanywhere.tech/v1",
        # base_url="https://api.chatanywhere.org/v1"
        timeout=20.0,  # 设置默认超时时间
    )
except Exception as e:
    # 如果初始化失败 (例如，没有设置 API Key)，则将 client 设为 None
    client = None
    print(f"--- 警告: OpenAI 客户端初始化失败: {e} ---")
    print("--- LLM API 集成功能将不可用 ---")


class LLMExecutionResult:
    """封装 LLM 执行结果的数据类"""

    def __init__(
        self, success: bool, content: str = None, usage: dict = None, error: str = None
    ):
        self.success = success
        self.content = content
        self.usage = usage
        self.error = error


def execute_prompt(prompt_content: str, variables: dict) -> LLMExecutionResult:
    """
    执行一个 Prompt，包括变量替换和调用 LLM API
    :param prompt_content: 包含模板变量的 Prompt 字符串 (e.g., "你好, {{name}}")
    :param variables: 用于替换模板变量的字典 (e.g., {"name": "Alice"})
    :return: 一个 LLMExecutionResult 实例
    """
    if not client:
        return LLMExecutionResult(
            success=False, error="OpenAI client is not initialized."
        )

    # 2. 使用 Jinja2 进行安全的变量替换
    try:
        template = Template(prompt_content)
        final_prompt = template.render(variables)
    except Exception as e:
        print(f"--- [LLM Client Error] An unexpected error occurred: {e} ---")
        return LLMExecutionResult(
            success=False, error=f"Template rendering failed: {e}"
        )

    # 3. 调用 OpenAI API 并处理潜在的错误
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": final_prompt,
                }
            ],
            model="gpt-3.5-turbo",  # 或者使用更新的模型
        )

        content = chat_completion.choices[0].message.content
        usage_dict = chat_completion.usage.model_dump()  # Pydantic v2 使用 model_dump()

        return LLMExecutionResult(success=True, content=content, usage=usage_dict)

    except APITimeoutError:
        print("--- LLM CLIENT ERROR: Request timed out. ---")
        return LLMExecutionResult(success=False, error="OpenAI API request timed out.")
    except APIConnectionError as e:
        print(f"--- LLM CLIENT ERROR: Connection error: {e} ---")
        return LLMExecutionResult(
            success=False, error="Failed to connect to OpenAI API."
        )
    except RateLimitError:
        print("--- LLM CLIENT ERROR: Rate limit exceeded. ---")
        return LLMExecutionResult(
            success=False, error="OpenAI API rate limit exceeded."
        )
    except Exception as e:
        # --- 在这里添加详细的日志打印 ---
        print(f"--- LLM CLIENT UNEXPECTED ERROR: {type(e).__name__}: {e} ---")
        return LLMExecutionResult(
            success=False, error=f"An unexpected error occurred: {e}"
        )
