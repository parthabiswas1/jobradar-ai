"""
Email digest sender.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from utils.db import get_config, get_jobs, add_log


def build_digest_html(jobs: list) -> str:
    rows = ""
    for job in jobs[:30]:  # max 30 per digest
        score = job.get("ai_score", "N/A")
        score_color = "#16a34a" if (isinstance(score, int) and score >= 75) else (
            "#ca8a04" if (isinstance(score, int) and score >= 50) else "#dc2626"
        )
        rows += f"""
        <tr>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;">
            <a href="{job.get('url','#')}" style="color:#2563eb;font-weight:600;text-decoration:none;">
              {job.get('title','')}
            </a><br>
            <span style="font-size:13px;color:#6b7280;">
              {job.get('company','')} · {job.get('location','')}
              {'· 🌐 Remote' if job.get('remote') else ''}
            </span>
          </td>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="color:{score_color};font-weight:700;font-size:16px;">{score}</span>
          </td>
          <td style="padding:12px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#374151;">
            {job.get('ai_reason','')[:200]}
          </td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#111;">
      <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:24px;border-radius:12px 12px 0 0;">
        <h1 style="color:white;margin:0;font-size:22px;">🎯 AI Job Hunter Digest</h1>
        <p style="color:#bfdbfe;margin:4px 0 0;">{datetime.now().strftime('%A, %B %d %Y · %I:%M %p')}</p>
      </div>
      <div style="background:#f8fafc;padding:16px 24px;border:1px solid #e2e8f0;border-top:none;">
        <p style="margin:0;color:#374151;">
          Found <strong>{len(jobs)} new jobs</strong> matching your profile today.
        </p>
      </div>
      <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e2e8f0;border-top:none;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 8px;text-align:left;font-size:13px;color:#475569;">Job</th>
            <th style="padding:10px 8px;text-align:center;font-size:13px;color:#475569;">AI Score</th>
            <th style="padding:10px 8px;text-align:left;font-size:13px;color:#475569;">Why It Matches</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <div style="background:#f8fafc;padding:16px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
        <p style="margin:0;font-size:12px;color:#9ca3af;">
          Sent by AI Job Hunter · <a href="#" style="color:#2563eb;">Manage preferences</a>
        </p>
      </div>
    </body>
    </html>
    """


def send_digest(jobs: list = None) -> bool:
    """Send email digest. If jobs not provided, uses new ranked jobs from DB."""
    config = get_config()
    
    if not config.get("email_to") or not config.get("smtp_password"):
        add_log("error", "Email not configured. Set email settings first.", "email")
        return False
    
    if jobs is None:
        all_jobs = get_jobs()
        jobs = [j for j in all_jobs if j.get("filter_passed") and j.get("ai_score", 0) >= config.get("min_ai_score", 60)]
    
    if not jobs:
        add_log("info", "No qualifying jobs to send in digest.", "email")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 {len(jobs)} New Job Matches – {datetime.now().strftime('%b %d')}"
        msg["From"] = config.get("email_from") or config.get("email_to")
        msg["To"] = config.get("email_to")
        
        html_body = build_digest_html(jobs)
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(config.get("smtp_host", "smtp.gmail.com"),
                          int(config.get("smtp_port", 587))) as server:
            server.starttls()
            server.login(
                config.get("email_from") or config.get("email_to"),
                config.get("smtp_password")
            )
            server.send_message(msg)
        
        add_log("info", f"Digest sent with {len(jobs)} jobs to {config['email_to']}", "email")
        return True
    except Exception as e:
        add_log("error", f"Failed to send digest: {e}", "email")
        return False
