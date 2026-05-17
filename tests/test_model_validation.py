import unittest
import warnings
from unittest.mock import patch

import pytest

from tradingagents.llm_clients.base_client import BaseLLMClient
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.model_catalog import get_known_models
from tradingagents.llm_clients.validators import validate_model


class DummyLLMClient(BaseLLMClient):
    def __init__(self, provider: str, model: str):
        self.provider = provider
        super().__init__(model)

    def get_llm(self):
        self.warn_if_unknown_model()
        return object()

    def validate_model(self) -> bool:
        return validate_model(self.provider, self.model)


@pytest.mark.unit
class ModelValidationTests(unittest.TestCase):
    def test_cli_catalog_models_are_all_validator_approved(self):
        for provider, models in get_known_models().items():
            if provider in ("ollama", "openrouter"):
                continue

            for model in models:
                with self.subTest(provider=provider, model=model):
                    self.assertTrue(validate_model(provider, model))

    def test_unknown_model_emits_warning_for_strict_provider(self):
        client = DummyLLMClient("openai", "not-a-real-openai-model")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client.get_llm()

        self.assertEqual(len(caught), 1)
        self.assertIn("not-a-real-openai-model", str(caught[0].message))
        self.assertIn("openai", str(caught[0].message))

    def test_openrouter_and_ollama_accept_custom_models_without_warning(self):
        for provider in ("openrouter", "ollama"):
            client = DummyLLMClient(provider, "custom-model-name")

            with self.subTest(provider=provider):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    client.get_llm()

                self.assertEqual(caught, [])

    def test_minimax_factory_uses_openai_compatible_client(self):
        with patch.dict(
            "os.environ",
            {"MINIMAX_API_KEY": "test-key"},
            clear=False,
        ), patch("tradingagents.llm_clients.openai_client.MinimaxChatOpenAI") as chat_cls:
            client = create_llm_client("minimax", "MiniMax-M2.7-highspeed")
            llm = client.get_llm()

        self.assertIs(llm, chat_cls.return_value)
        self.assertEqual(client.provider, "minimax")
        chat_cls.assert_called_once_with(
            model="MiniMax-M2.7-highspeed",
            base_url="https://api.minimax.io/v1",
            api_key="test-key",
        )

    def test_xiaomi_models_are_validator_approved(self):
        known = get_known_models()

        self.assertIn("xiaomi", known)
        self.assertIn("mimo-v2.5-pro", known["xiaomi"])
        self.assertTrue(validate_model("xiaomi", "mimo-v2.5-pro"))

    def test_xiaomi_factory_uses_openai_compatible_chat_client(self):
        with patch.dict(
            "os.environ",
            {
                "XIAOMI_API_KEY": "xiaomi-test-key",
                "XIAOMI_BASE_URL": "https://xiaomi-proxy.example/v1",
            },
            clear=False,
        ), patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI") as chat_cls:
            client = create_llm_client("xiaomi", "mimo-v2.5-pro")
            llm = client.get_llm()

        self.assertIs(llm, chat_cls.return_value)
        self.assertEqual(client.provider, "xiaomi")
        chat_cls.assert_called_once_with(
            model="mimo-v2.5-pro",
            base_url="https://xiaomi-proxy.example/v1",
            api_key="xiaomi-test-key",
        )
