"""Hand-laid diagram for a LinkedIn post (1080x1350, 4:5 portrait).
Uses the official AWS icons shipped with the `diagrams` package.
Regenerate with: python3 docs/linkedin_diagram.py"""

from pathlib import Path

import diagrams
from PIL import Image, ImageDraw, ImageFont

ICONS = Path(diagrams.__file__).parent.parent / "resources"
OUT = Path(__file__).parent / "linkedin-architecture.png"

W, H = 1080, 1350
NAVY, INK, MUTED = (31, 59, 99), (22, 25, 31), (84, 92, 105)
ACCENT, LINE, RED = (31, 78, 156), (120, 130, 145), (192, 57, 43)
FONT = "/System/Library/Fonts/Helvetica.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
S = 112  # icon size


def icon(path, cx, cy, label, sub=None):
    im = Image.open(ICONS / path).convert("RGBA").resize((S, S), Image.LANCZOS)
    img.paste(im, (cx - S // 2, cy - S // 2), im)
    f = font(25, True)
    d.text((cx, cy + S // 2 + 12), label, font=f, fill=INK, anchor="ma")
    if sub:
        d.text((cx, cy + S // 2 + 44), sub, font=font(21), fill=MUTED, anchor="ma")


def arrow(x1, y1, x2, y2, color=LINE, dashed=False):
    if dashed:
        n = 14
        for i in range(n):
            if i % 2 == 0:
                a, b = i / n, (i + 1) / n
                d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                        (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=color, width=4)
    else:
        d.line([(x1, y1), (x2, y2)], fill=color, width=4)
    # arrow head
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 16
    p1 = (x2 - L * math.cos(ang - 0.45), y2 - L * math.sin(ang - 0.45))
    p2 = (x2 - L * math.cos(ang + 0.45), y2 - L * math.sin(ang + 0.45))
    d.polygon([(x2, y2), p1, p2], fill=color)


# ---------- Header ----------
d.rectangle([0, 0, W, 14], fill=NAVY)
d.text((60, 50), "Serverless sales data pipeline", font=font(50, True), fill=INK)
d.text((60, 114), "on AWS, built with Terraform", font=font(34), fill=ACCENT)

# ---------- Happy path ----------
R1 = 275   # upload row
X = [190, 540, 890]
icon("onprem/client/users.png", X[0], R1, "Branches", "upload sales CSV")
icon("aws/storage/simple-storage-service-s3.png", X[1], R1, "Raw files", "S3")
icon("aws/integration/simple-queue-service-sqs.png", X[2], R1, "Queue", "SQS, retries")
arrow(X[0] + 75, R1, X[1] - 75, R1)
arrow(X[1] + 75, R1, X[2] - 75, R1)

R2 = 525   # validate
icon("aws/compute/lambda.png", 540, R2, "Validate every row", "Lambda, Python")
arrow(X[2] - 40, R1 + 132, 610, R2 - 66)

R3 = 785   # outputs
icon("aws/storage/simple-storage-service-s3.png", X[0], R3, "Clean data", "and rejected rows")
icon("aws/database/dynamodb.png", X[1], R3, "Audit trail", "one record per file")
arrow(470, R2 + 132, X[0] + 40, R3 - 66)
arrow(X[1], R2 + 132, X[1], R3 - 66)

R4 = 1025  # reporting
icon("aws/analytics/athena.png", X[0], R4, "SQL reports", "Athena")
arrow(X[0], R3 + 132, X[0], R4 - 66)

# ---------- Failure path (right column) ----------
icon("aws/integration/simple-queue-service-sqs.png", X[2], R3 - 40, "Failed files", "after 3 tries")
icon("onprem/client/user.png", X[2], R4, "Email alert", "to a person")
arrow(X[2] + 40, R1 + 132, X[2] + 40, R3 - 106, RED, dashed=True)
arrow(X[2], R3 - 40 + 132, X[2], R4 - 66, RED, dashed=True)
d.text((X[2] + 56, (R1 + R3) // 2 - 70), "if it\nfails", font=font(21, True), fill=RED, spacing=4)

# ---------- Footer ----------
chips = ["Terraform", "GitHub Actions + OIDC", "No stored keys", "Runs at $0"]
x, y = 60, 1200
for c in chips:
    f = font(24, True)
    w = d.textlength(c, font=f) + 36
    d.rounded_rectangle([x, y, x + w, y + 50], radius=25, fill=(234, 240, 248), outline=(196, 210, 230))
    d.text((x + 18, y + 12), c, font=f, fill=ACCENT)
    x += w + 14
d.text((60, 1278), "github.com/gumagatsby/aws-serverless-sales-pipeline", font=font(22), fill=MUTED)

img.save(OUT, optimize=True)
print(OUT)
