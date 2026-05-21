import json
import unittest

from assistant_service import AssistantService, MAX_ANSWER_INPUT_CHARS, MAX_EVIDENCE_MESSAGES


class LargeAnswerDatabase:
    def __init__(self):
        self.calls = []

    def search_indexed_messages(self, query, limit):
        self.calls.append((query, limit))
        max_size_text = "x" * 4096
        return [
            {
                "chat_title": f"Chat {index}",
                "sender_name": f"Sender {index}",
                "message_timestamp": 1716163200 + index,
                "message_id": index,
                "text": max_size_text,
            }
            for index in range(limit)
        ]


class CapturingModel:
    def __init__(self):
        self.prompts = []

    async def generate_text(self, prompt):
        self.prompts.append(prompt)
        return "bounded answer"


class AssistantAnswerPromptBoundingTests(unittest.IsolatedAsyncioTestCase):
    async def test_answer_prompt_evidence_text_is_bounded_for_large_indexed_messages(self):
        database = LargeAnswerDatabase()
        model = CapturingModel()

        answer = await AssistantService(database, model).answer_question("What changed?")

        self.assertIn("bounded answer", answer)
        self.assertIn("Sources:", answer)
        self.assertIn("Chat 0", answer)
        self.assertIn("#0", answer)
        self.assertIn("Chat 11", answer)
        self.assertIn("#11", answer)
        self.assertEqual([("What changed?", MAX_EVIDENCE_MESSAGES)], database.calls)
        self.assertEqual(1, len(model.prompts))

        prompt = model.prompts[0]
        self.assertIn("untrusted", prompt.lower())
        payload = json.loads(prompt.split("JSON payload:\n", 1)[1])

        self.assertEqual("What changed?", payload["question"])
        self.assertEqual(MAX_EVIDENCE_MESSAGES, len(payload["evidence"]))
        self.assertEqual("Chat 0", payload["evidence"][0]["chat_title"])
        self.assertEqual("Sender 0", payload["evidence"][0]["sender_name"])
        self.assertEqual(0, payload["evidence"][0]["message_id"])
        total_evidence_text = sum(len(message["text"]) for message in payload["evidence"])
        self.assertLessEqual(total_evidence_text, MAX_ANSWER_INPUT_CHARS)
        self.assertIn("[truncated", payload["evidence"][0]["text"])
