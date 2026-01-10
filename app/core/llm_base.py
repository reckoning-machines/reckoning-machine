from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> dict:
        """
        Args:
            prompt (str): The input prompt for the LLM.
        Returns:
            dict: {
                "raw_text": str,           # the raw text from the LLM
                "parsed_json": dict|None,  # dict if raw_text is JSON parsable, else None
            }
        """
        pass
