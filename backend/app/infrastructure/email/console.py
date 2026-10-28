import logging

log = logging.getLogger("shoppilot.email")


class ConsoleEmailSender:
    """Development email sender: writes the email to the server log.
    Replace with an SMTP/transactional-email adapter before the pilot launch."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        log.info("EMAIL to=%s subject=%s\n%s", to, subject, body)
