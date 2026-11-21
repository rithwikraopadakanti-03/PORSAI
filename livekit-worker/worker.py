
"""
SUNRISE SALON - AI VOICE RECEPTIONIST

STT : Groq Whisper
LLM : Groq GPT-OSS 120B
TTS : Groq Orpheus English
VAD : Silero
RTC : LiveKit Cloud

BOOKING:
FastAPI + PostgreSQL
"""

import os
import re
import logging

from datetime import datetime, date, time
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext, function_tool
from livekit.plugins import groq, silero


# =====================================================
# 1. CONFIGURATION
# =====================================================

load_dotenv()

TZ = ZoneInfo("Asia/Kolkata")

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
).rstrip("/")

STT_MODEL = "whisper-large-v3-turbo"
LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "hannah"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("SunriseSalon")

REQUIRED_KEYS = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "GROQ_API_KEY",
]

missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]

if missing:
    raise RuntimeError(
        f"Missing environment variables: {', '.join(missing)}"
    )


# =====================================================
# 2. API HELPERS
# =====================================================

async def api_get(path, params=None):

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.get(
            f"{API_BASE_URL}{path}",
            params=params
        )

        response.raise_for_status()

        return response.json()


async def api_post(path, payload):

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.post(
            f"{API_BASE_URL}{path}",
            json=payload
        )

        if not response.is_success:

            try:
                detail = response.json().get(
                    "detail",
                    response.text
                )
            except Exception:
                detail = response.text

            raise RuntimeError(
                f"Booking API error {response.status_code}: {detail}"
            )

        return response.json()


def find_service(services, requested_name):

    query = re.sub(
        r"[^a-z0-9 ]",
        "",
        requested_name.lower()
    )

    # Men's haircut
    if "men" in query or "male" in query:

        for service in services:

            name = service["name"].lower()

            if "men" in name and "haircut" in name:
                return service

    # Women's haircut
    if "women" in query or "female" in query:

        for service in services:

            name = service["name"].lower()

            if "women" in name and "haircut" in name:
                return service

    # Exact match
    for service in services:

        name = re.sub(
            r"[^a-z0-9 ]",
            "",
            service["name"].lower()
        )

        if name == query:
            return service

    # Partial match
    for service in services:

        name = service["name"].lower()

        if query and (
            query in name or name in query
        ):
            return service

    return None


async def get_slot_information(
    service_name,
    appointment_date,
    appointment_time
):

    try:

        requested_date = date.fromisoformat(
            appointment_date
        )

        requested_time = time.fromisoformat(
            appointment_time
        )

        services = await api_get("/api/services")

        service = find_service(
            services,
            service_name
        )

        if not service:

            return {
                "success": False,
                "message": f"Service not found: {service_name}"
            }

        availability = await api_get(
            "/api/availability",
            params={
                "service_id": service["id"],
                "date": requested_date.isoformat()
            }
        )

        requested_datetime = datetime.combine(
            requested_date,
            requested_time,
            tzinfo=TZ
        )

        available_slots = availability.get(
            "available_slots",
            []
        )

        slot_available = any(
            datetime.fromisoformat(slot).astimezone(TZ)
            == requested_datetime
            for slot in available_slots
        )

        return {
            "success": True,
            "available": slot_available,
            "service": service,
            "stylist": availability["stylist"],
            "datetime": requested_datetime.isoformat(),
            "available_slots": available_slots
        }

    except Exception as error:

        logger.exception("Availability check failed")

        return {
            "success": False,
            "message": str(error)
        }


# =====================================================
# 3. SUNRISE SALON PERSONALITY
# =====================================================

SYSTEM_PROMPT = f"""
You are the official AI receptionist of SUNRISE SALON.

Never call yourself PorsAI.

CURRENT DATE:
{datetime.now(TZ).strftime("%A, %d %B %Y")}

TIMEZONE:
Asia/Kolkata (Indian Standard Time).

YOUR PERSONALITY:

- Friendly and professional.
- Natural conversational English.
- Helpful and polite.
- Short spoken responses.
- Never give empty responses.
- Never invent information.

SALON INFORMATION:

Name: Sunrise Salon

Address:
12 Lake Road, Indiranagar, Bengaluru.

Hours:
Monday to Saturday.
Closed Sundays.

SERVICES:

Women's haircut: Rs. 600
Men's haircut: Rs. 400
Blow dry: Rs. 500
Hair colour: From Rs. 2,500
Hair spa: Rs. 1,200
Facial: Rs. 1,500
Clean-up: Rs. 800

STYLISTS:

Anita Rao:
Monday-Saturday, 10 AM-2 PM.
Haircuts and styling.

Rahul Shetty:
Tuesday, Thursday, Saturday, 4 PM-8 PM.
Hair colour and hair spa.

Kavya Nair:
Monday, Wednesday, Friday, 9 AM-1 PM.
Facials and clean-ups.

PAYMENTS:
Cash, UPI and cards.

BOOKING RULES - VERY IMPORTANT:

You have access to REAL appointment booking tools.

When a customer requests an appointment:

STEP 1:
Understand the requested service, date and time.

STEP 2:
Convert relative dates such as tomorrow and next Monday
using the current date above.

STEP 3:
Call check_appointment_availability.
Never guess availability.

STEP 4:
If the slot is unavailable:
Tell the customer and offer available alternatives.

STEP 5:
If the slot is available:
Ask the customer for their full name and phone number
if these details have not already been provided.

STEP 6:
Read back the complete appointment details:
- Customer name
- Service
- Date
- Time
- Stylist
- Price

Ask:
"Shall I confirm this appointment?"

STEP 7:
Only after the customer explicitly agrees,
call book_appointment with customer_confirmed=True.

STEP 8:
Wait for the actual API result.

STEP 9:
If the API confirms success, tell the customer:
"Your appointment is successfully booked at
Sunrise Salon."

Provide the real booking ID.

IMPORTANT:

- Never say a booking is confirmed before the API succeeds.
- Never invent booking IDs.
- Never skip the availability check.
- Never invent customer names or phone numbers.
- Never book without explicit customer confirmation.
- If the API fails, explain that booking could not be completed.
- Never claim that someone will contact the customer
  unless an actual follow-up system is configured.

APPOINTMENT CANCELLATION AND RESCHEDULING:

Do not claim these actions are completed unless
the corresponding API operation succeeds.

Keep all conversations professional and focused
on Sunrise Salon.
"""


# =====================================================
# 4. AI RECEPTIONIST WITH BOOKING TOOLS
# =====================================================

class SunriseSalonReceptionist(Agent):

    def __init__(self):

        super().__init__(
            instructions=SYSTEM_PROMPT
        )

    # -------------------------------------------------
    # TOOL 1: CHECK APPOINTMENT AVAILABILITY
    # -------------------------------------------------

    @function_tool()
    async def check_appointment_availability(
        self,
        context: RunContext,
        service_name: str,
        appointment_date: str,
        appointment_time: str
    ) -> str:
        """
        Check actual appointment availability in the
        Sunrise Salon database.

        Args:
            service_name: Requested service, for example Men's haircut.
            appointment_date: Date in YYYY-MM-DD format.
            appointment_time: Time in 24-hour HH:MM format.
        """

        logger.info(
            "Checking availability: %s %s %s",
            service_name,
            appointment_date,
            appointment_time
        )

        result = await get_slot_information(
            service_name,
            appointment_date,
            appointment_time
        )

        if not result["success"]:

            return (
                "Could not check availability. "
                + result["message"]
            )

        if result["available"]:

            service = result["service"]

            return (
                f"AVAILABLE. "
                f"Service: {service['name']}. "
                f"Price: {service['price']}. "
                f"Stylist: {result['stylist']}. "
                f"Date and time: {result['datetime']}. "
                "Ask the customer for their full name "
                "and phone number before proceeding."
            )

        alternatives = result["available_slots"]

        if alternatives:

            readable = [
                datetime.fromisoformat(slot)
                .astimezone(TZ)
                .strftime("%I:%M %p")
                for slot in alternatives
            ]

            return (
                "REQUESTED SLOT UNAVAILABLE. "
                "Available alternatives: "
                + ", ".join(readable)
            )

        return (
            "No appointments are available for this "
            "service on that date."
        )

    # -------------------------------------------------
    # TOOL 2: CREATE REAL APPOINTMENT
    # -------------------------------------------------

    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        service_name: str,
        appointment_date: str,
        appointment_time: str,
        customer_name: str,
        customer_phone: str,
        customer_confirmed: bool
    ) -> str:
        """
        Create a real appointment in the Sunrise Salon
        PostgreSQL database.

        Only call this after:
        1. Availability was checked.
        2. Customer name and phone were collected.
        3. Details were read back.
        4. Customer explicitly agreed.

        Args:
            service_name: Requested salon service.
            appointment_date: YYYY-MM-DD.
            appointment_time: HH:MM in 24-hour format.
            customer_name: Customer's actual full name.
            customer_phone: Customer's actual phone number.
            customer_confirmed: True only after explicit
                customer confirmation.
        """

        if not customer_confirmed:

            return (
                "Booking not created. Read back the "
                "appointment details and obtain explicit "
                "customer confirmation first."
            )

        if not customer_name.strip() or not customer_phone.strip():

            return (
                "Booking requires the customer's name "
                "and phone number."
            )

        # Do not allow interruptions during database write.
        context.disallow_interruptions()

        logger.info(
            "Creating appointment for %s",
            customer_name
        )

        try:

            # Recheck availability immediately before booking.
            result = await get_slot_information(
                service_name,
                appointment_date,
                appointment_time
            )

            if not result["success"]:

                return (
                    "Booking failed: "
                    + result["message"]
                )

            if not result["available"]:

                return (
                    "This appointment slot is no longer "
                    "available. Please select another time."
                )

            service = result["service"]

            # Create timezone-aware appointment.
            starts_at = result["datetime"]

            payload = {
                "service_id": service["id"],
                "starts_at": starts_at,
                "customer_name": customer_name.strip(),
                "customer_phone": customer_phone.strip()
            }

            # ACTUAL DATABASE BOOKING
            booking = await api_post(
                "/api/bookings",
                payload
            )

            logger.info(
                "BOOKING SUCCESSFUL: %s",
                booking["booking_id"]
            )

            return (
                "BOOKING SUCCESSFUL. "
                f"Booking ID: {booking['booking_id']}. "
                f"Customer: {customer_name}. "
                f"Service: {booking['service']}. "
                f"Stylist: {booking['stylist']}. "
                f"Date and time: {booking['starts_at']}. "
                f"Status: {booking['status']}. "
                f"Price: {service['price']}. "
                "Tell the customer the appointment "
                "is officially confirmed."
            )

        except Exception as error:

            logger.exception("BOOKING FAILED")

            return (
                "The appointment could not be confirmed. "
                f"Reason: {str(error)}. "
                "Do not claim that it was booked."
            )


# =====================================================
# 5. LIVEKIT WORKER
# =====================================================

async def entrypoint(ctx: agents.JobContext):

    logger.info("=" * 55)
    logger.info("SUNRISE SALON AI RECEPTIONIST STARTING")
    logger.info("=" * 55)

    try:

        # Connect to LiveKit
        await ctx.connect()

        logger.info("LIVEKIT CONNECTED")

        # Speech recognition
        stt = groq.STT(
            model=STT_MODEL,
            language="en"
        )

        logger.info("WHISPER STT READY")

        # AI brain with tool calling
        llm = groq.LLM(
            model=LLM_MODEL,
            tool_choice="auto",
            parallel_tool_calls=False,
            reasoning_effort="low"
        )

        logger.info("GROQ LLM READY")

        # Voice generation
        tts = groq.TTS(
            model=TTS_MODEL,
            voice=TTS_VOICE
        )

        logger.info("ORPHEUS TTS READY")

        # Voice activity detection
        vad = silero.VAD.load()

        logger.info("SILERO VAD READY")

        # Create voice session
        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad
        )

        # Start receptionist
        receptionist = SunriseSalonReceptionist()

        await session.start(
            room=ctx.room,
            agent=receptionist
        )

        logger.info("=" * 55)
        logger.info("SUNRISE SALON RECEPTIONIST CONNECTED")
        logger.info("ROOM: %s", ctx.room.name)
        logger.info("BOOKING TOOLS: ENABLED")
        logger.info("=" * 55)

        # Greeting
        await session.generate_reply(
            instructions=(
                "Greet the caller. Say: "
                "Hello! Welcome to Sunrise Salon. "
                "How may I help you today?"
            )
        )

        logger.info("WELCOME GREETING COMPLETED")

    except Exception:

        logger.exception(
            "SUNRISE SALON WORKER ERROR"
        )

        raise


# =====================================================
# 6. START APPLICATION
# =====================================================

if __name__ == "__main__":

    logger.info("Starting Sunrise Salon LiveKit worker")

    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="sunrise-salon-agent"
        )
    )
