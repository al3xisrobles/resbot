"""Email utility for sending reservation-related notifications via Resend."""

import logging
import os
from datetime import datetime

import resend
import sentry_sdk

logger = logging.getLogger(__name__)

APP_URL = os.getenv("APP_URL", "https://resbot.app")
FROM_ADDRESS = os.getenv("RESEND_FROM_ADDRESS", "Resbot <notifications@resbot.app>")

_LOGO_URL = "https://resbot.org/assets/ResbotLogoRedWithText-BztMXUo0.svg"
_LOGO_IMG = (
    '<img src="%s" width="180" height="40" alt="Resbot"'
    ' style="display:block;border:0;" />' % _LOGO_URL
)


def send_failed_reservation_email(
    user_email,
    user_first_name,
    venue_name,
    reservation_date,
    reservation_hour,
    reservation_minute,
    party_size,
    job_id,
    email_summary,
):
    """Send a failed reservation notification email to the user.

    Args:
        user_email: Recipient email address.
        user_first_name: User's first name for personalization.
        venue_name: Name of the restaurant/venue.
        reservation_date: datetime.date object for the reservation.
        reservation_hour: Integer hour (24-hour format).
        reservation_minute: Integer minute.
        party_size: Number of guests.
        job_id: Unique job identifier for tagging.
        email_summary: Short LLM-generated explanation of why the attempt failed.

    Returns:
        True on success, False on any failure (never raises).
    """
    try:
        resend.api_key = os.getenv("RESEND_API_KEY")

        if isinstance(reservation_date, str):
            reservation_date = datetime.strptime(reservation_date, "%Y-%m-%d").date()

        dt = datetime.combine(reservation_date, datetime.min.time()).replace(
            hour=reservation_hour, minute=reservation_minute
        )
        display_date = reservation_date.strftime("%A, %B %-d, %Y")
        display_time = dt.strftime("%-I:%M %p")
        details_url = "%s/reservations" % APP_URL

        html_body = _render_html(
            user_first_name,
            venue_name,
            display_date,
            display_time,
            party_size,
            email_summary,
            details_url,
        )
        plain_body = _render_plain_text(
            user_first_name,
            venue_name,
            display_date,
            display_time,
            party_size,
            email_summary,
            details_url,
        )

        params = {
            "from": FROM_ADDRESS,
            "to": [user_email],
            "subject": "Your reservation attempt at %s was unsuccessful" % venue_name,
            "html": html_body,
            "text": plain_body,
            "tags": [
                {"name": "category", "value": "reservation_failed"},
                {"name": "job_id", "value": job_id},
            ],
        }

        result = resend.Emails.send(params)
        logger.info("Failed-reservation email sent to %s, email_id=%s", user_email, result.get("id"))
        return True

    except Exception as e:  # pylint: disable=broad-except
        sentry_sdk.capture_exception(e)
        logger.error("Failed to send reservation failure email to %s: %s", user_email, e)
        return False


def _render_html(first_name, venue_name, display_date, display_time, party_size, email_summary, details_url):
    """Render the HTML email body for a failed reservation notification.

    Args:
        first_name: User's first name.
        venue_name: Restaurant/venue name.
        display_date: Human-readable date string.
        display_time: Human-readable time string.
        party_size: Number of guests.
        email_summary: Short explanation of the failure.
        details_url: URL to the reservations dashboard.

    Returns:
        HTML string.
    """
    party_label = "guest" if party_size == 1 else "guests"
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reservation Unsuccessful</title>
</head>
<body style="margin:0;padding:0;background-color:#f9f9f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <!-- Header -->
  <table width="100%%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f9f9f9;">
    <tr>
      <td align="center" style="padding:32px 16px 8px 16px;">
        %(logo_img)s
      </td>
    </tr>
  </table>

  <!-- Body -->
  <table width="100%%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f9f9f9;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="100%%" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;background-color:#ffffff;border-radius:12px;
                      overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
          <tr>
            <td style="padding:32px 32px 24px 32px;">

              <!-- Badge -->
              <div style="margin-bottom:20px;">
                <span style="display:inline-block;background-color:#e63946;color:#ffffff;
                             font-size:13px;font-weight:600;padding:6px 14px;
                             border-radius:999px;letter-spacing:0.3px;">
                  Reservation Unsuccessful
                </span>
              </div>

              <!-- Greeting -->
              <p style="margin:0 0 12px 0;font-size:14px;color:#444444;">
                Hi %(first_name)s,
              </p>
              <p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#444444;">
                Unfortunately, we weren't able to secure your reservation this time.
              </p>
              <p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#444444;">
                Reservation bots are inherently competitive—slots for popular venues 
                are often contested by multiple bots simultaneously, and release times 
                don't always match expectations. Failures can also be on our end, and
                we own that (this is a new product).
              </p>
              <p style="margin:0 0 24px 0;font-size:14px;line-height:1.7;color:#444444;">
                You have unlimited attempts, so feel free to try again. You can also use
                the discovery feature to find the exact times slots drop
                at your venue before trying again.
              </p>

              <!-- Details box -->
              <table width="100%%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#f4f4f5;border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <p style="margin:0 0 6px 0;font-size:16px;font-weight:700;color:#111111;">
                      %(venue_name)s
                    </p>
                    <p style="margin:0 0 4px 0;font-size:14px;color:#555555;">
                      %(display_date)s
                    </p>
                    <p style="margin:0 0 4px 0;font-size:14px;color:#555555;">
                      %(display_time)s
                    </p>
                    <p style="margin:0;font-size:14px;color:#555555;">
                      %(party_size)s %(party_label)s
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Separator -->
              <hr style="border:none;border-top:1px solid #ebebeb;margin:0 0 20px 0;" />

              <!-- Summary -->
              <p style="margin:0 0 8px 0;font-size:11px;font-weight:600;letter-spacing:0.6px;
                        text-transform:uppercase;color:#aaaaaa;">
                What happened this time
              </p>
              <p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:#444444;">
                %(email_summary)s
              </p>

              <!-- Separator -->
              <hr style="border:none;border-top:1px solid #ebebeb;margin:0 0 20px 0;" />

              <!-- Improvement note -->
              <p style="margin:0 0 28px 0;font-size:13px;line-height:1.7;color:#888888;">
                We're actively working to improve our booking success rate. For a full
                breakdown of this attempt, check the Notes section in your dashboard.
              </p>

              <!-- CTA button -->
              <table cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="left"
                      style="background-color:#0f0f0f;border-radius:8px;">
                    <a href="%(details_url)s"
                       style="display:inline-block;padding:12px 28px;color:#ffffff;
                              font-size:14px;font-weight:600;text-decoration:none;
                              letter-spacing:0.2px;">
                      View in Dashboard &rarr;
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Footer -->
  <table width="100%%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center" style="padding:16px;">
        <p style="margin:0;font-size:12px;color:#aaaaaa;">
          &copy; 2026 Resbot
        </p>
      </td>
    </tr>
  </table>

</body>
</html>""" % {
        "first_name": first_name,
        "venue_name": venue_name,
        "display_date": display_date,
        "display_time": display_time,
        "party_size": party_size,
        "party_label": party_label,
        "email_summary": email_summary,
        "details_url": details_url,
        "logo_img": _LOGO_IMG,
    }


def _render_plain_text(first_name, venue_name, display_date, display_time, party_size, email_summary, details_url):
    """Render the plain-text fallback email for a failed reservation notification.

    Args:
        first_name: User's first name.
        venue_name: Restaurant/venue name.
        display_date: Human-readable date string.
        display_time: Human-readable time string.
        party_size: Number of guests.
        email_summary: Short explanation of the failure.
        details_url: URL to the reservations dashboard.

    Returns:
        Plain text string.
    """
    party_label = "guest" if party_size == 1 else "guests"
    return (
        "Hi %s,\n\n"
        "RESERVATION UNSUCCESSFUL\n\n"
        "Unfortunately, your reservation attempt at %s was not successful.\n\n"
        "--- Reservation Details ---\n"
        "Venue:       %s\n"
        "Date:        %s\n"
        "Time:        %s\n"
        "Party size:  %s %s\n"
        "---------------------------\n\n"
        "%s\n\n"
        "We're actively working to improve our bot's success rate. For a detailed "
        "breakdown of what happened, check the Notes section in your dashboard.\n\n"
        "View in Dashboard: %s\n\n"
        "---\n"
        "© 2026 Resbot"
    ) % (
        first_name,
        venue_name,
        venue_name,
        display_date,
        display_time,
        party_size,
        party_label,
        email_summary,
        details_url,
    )
