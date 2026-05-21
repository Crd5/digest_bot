class GeminiModelClient:
    def __init__(self, gemini_client, model_name="gemini-2.5-pro"):
        self.gemini_client = gemini_client
        self.model_name = model_name

    async def generate_text(self, prompt: str) -> str:
        response = await self.gemini_client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return (response.text or "").strip()
