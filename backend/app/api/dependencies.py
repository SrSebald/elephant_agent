from app.repositories.ticket_repository import ticket_repository
from app.services.ticket_service import ticket_service


def get_ticket_repository():
    return ticket_repository


def get_ticket_service():
    return ticket_service
