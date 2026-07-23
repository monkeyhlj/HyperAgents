from openai import OpenAI

client = OpenAI(
    # 1. 替换为 NVIDIA 的 API 地址
    base_url="https://integrate.api.nvidia.com/v1",
    # 2. 替换为你刚申请的 NVIDIA API Key
    api_key="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"
)

# 3. 调用模型，比如使用免费的 GLM-5.2 模型
response = client.chat.completions.create(
    model="z-ai/glm-5.2",  # 指定具体的免费模型
    messages=[
        {"role": "user", "content": "你是什么大模型"}
    ]
)

print(response.choices[0].message.content)