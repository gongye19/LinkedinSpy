from app.config import Settings


def test_settings_default_schedule():
    settings = Settings()

    assert settings.schedule_cron == "0 19 * * *"
