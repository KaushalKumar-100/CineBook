from io import BytesIO
from typing import Annotated

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from app.dependencies import DbSession, get_current_user
from app.models import Booking, BookingTicket, User

router = APIRouter(prefix="/bookings", tags=["Booking tickets"])

@router.get("/{booking_id}/ticket/pdf")
def download_booking_ticket_pdf(booking_id: int, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    """Download a printable PDF ticket for its owner or an administrator."""
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "confirmed" or not booking.ticket_code:
        raise HTTPException(status_code=409, detail="A confirmed ticket is not available for this booking")
    ticket = db.scalar(select(BookingTicket).where(BookingTicket.booking_id == booking.id, BookingTicket.ticket_code == booking.ticket_code))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket record not found")
    session = booking.session
    movie, event = session.movie, session.event
    space = session.venue_space
    venue = space.venue
    title = movie.title if movie else (event.title if event else "CineBook event")
    city = venue.city.name if venue.city else ""
    qr = BytesIO()
    qrcode.make(ticket.ticket_code, box_size=7, border=4).save(qr, format="PNG")
    qr.seek(0)
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=22*mm, leftMargin=22*mm, topMargin=20*mm, bottomMargin=20*mm, title="CineBook ticket")
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("TicketHeading", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#172554"))
    centered = ParagraphStyle("TicketCentered", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#475569"))
    story = [Paragraph("CineBook", heading), Paragraph("Booking confirmation and entry pass", centered), Spacer(1, 8*mm), Paragraph(title, styles["Heading2"])]
    rows = [["Booking reference", booking.booking_reference], ["Ticket code", ticket.ticket_code], ["Venue", venue.name], ["Location", ", ".join(x for x in [venue.address, city] if x)], ["Screen / space", space.name], ["Show time", session.starts_at.strftime("%d %b %Y, %I:%M %p")], ["Status", booking.status.upper()], ["Amount", f"INR {booking.total_amount}"]]
    table = Table(rows, colWidths=[48*mm, 105*mm])
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EFF6FF")), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#CBD5E1")), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    story.extend([table, Spacer(1, 10*mm)])
    qr_image = Image(qr, width=48*mm, height=48*mm); qr_image.hAlign = "CENTER"
    story.extend([qr_image, Spacer(1, 4*mm), Paragraph("Present this QR code for ticket validation.", centered), Paragraph("CineBook demo bookings and simulated payments are not valid for admission to real venues.", styles["Italic"])])
    doc.build(story)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="cinebook-ticket-{booking.booking_reference}.pdf"'})
