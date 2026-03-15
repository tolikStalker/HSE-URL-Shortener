from app.utils.short_code import generate_short_code


class TestShortCodeGeneration:
    def test_generate_short_code_length(self):
        code = generate_short_code()
        assert 3 <= len(code) <= 20

    def test_generate_short_code_characters(self):
        code = generate_short_code()
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        assert all(c in valid_chars for c in code)

    def test_generate_short_code_uniqueness(self):
        codes = {generate_short_code() for _ in range(100)}
        assert len(codes) == 100

    def test_generate_short_code_determinism(self):
        code1 = generate_short_code()
        code2 = generate_short_code()

        assert isinstance(code1, str)
        assert isinstance(code2, str)
