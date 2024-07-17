from pydantic import BaseModel, Field
from typing import Optional, Type, List

from .register import register_toolkit_output_parser, ToolOutputParserCollection


class VenmoSendMoneyParameters(BaseModel):
    recipient_username: str = Field(..., description="The username of the recipient.")
    amount: float = Field(
        ..., gt=0, description="The amount of money to send, must be positive."
    )
    note: Optional[str] = Field(
        "",
        description="A note to include with the payment. Default is an empty string.",
    )


class VenmoSendMoneyResult(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the transaction was successful."
    )
    transaction_id: str = Field(
        ..., description="The unique identifier of the transaction, if successful."
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the transaction was unsuccessful."
    )


class VenmoSendMoneyReturns(BaseModel):
    result: VenmoSendMoneyResult = Field(
        ...,
        description="An object containing 'success' (boolean), 'transaction_id' (string), and 'error_message' (string).",
    )


@register_toolkit_output_parser()
class VenmoOutputParser(ToolOutputParserCollection):
    name: str = Field(default="Venmo")
    tool_name_to_output_parser: dict[str, Type[BaseModel]] = Field(
        default_factory=lambda: {"VenmoSendMoney": VenmoSendMoneyReturns}
    )


class DoctorTimeSlot(BaseModel):
    start_time: str = Field(
        ...,
        description="The start time of the available slot in the format 'YYYY-MM-DD HH:MM'.",
    )
    end_time: str = Field(
        ...,
        description="The end time of the available slot in the format 'YYYY-MM-DD HH:MM'.",
    )


class Doctor(BaseModel):
    id: str = Field(..., description="The unique identifier of the doctor.")
    name: str = Field(..., description="The name of the doctor.")
    specialty: str = Field(..., description="The specialty of the doctor.")
    location: str = Field(..., description="The location of the doctor.")
    available_time_slots: List[DoctorTimeSlot] = Field(
        ..., description="A list of available time slots for the doctor."
    )


class TeladocSearchDoctorsReturns(BaseModel):
    doctors: List[Doctor] = Field(
        ...,
        description="A list of doctors with their respective unique identifiers, names, specialties, locations, and available time slots.",
    )


class TeladocConsultDoctorReturns(BaseModel):
    consultation_id: str = Field(
        ..., description="A unique identifier for the consultation."
    )


class TeladocScheduleAppointmentReturns(BaseModel):
    appointment_id: Optional[str] = Field(
        None,
        description="A unique identifier for the appointment if successfully scheduled, otherwise null.",
    )
    success: bool = Field(
        ...,
        description="A boolean indicating whether the appointment was successfully scheduled.",
    )


class AppointmentDetails(BaseModel):
    appointment_id: str = Field(
        ..., description="The unique identifier of the appointment."
    )
    doctor_id: str = Field(..., description="The unique identifier of the doctor.")
    date: str = Field(
        ..., description="The date of the appointment in the format 'YYYY-MM-DD'."
    )
    time: str = Field(
        ..., description="The time of the appointment in the format 'HH:mm'."
    )
    reason: str = Field(..., description="The reason for the appointment.")
    status: str = Field(..., description="The status of the appointment.")


class TeladocManageAppointmentsReturns(BaseModel):
    appointment_details: AppointmentDetails = Field(
        ...,
        description="An object containing the appointment details, such as appointment_id, doctor_id, date, time, reason, and status.",
    )


class UserInfo(BaseModel):
    date_of_birth: str = Field(..., description="The user's date of birth.")
    location: str = Field(..., description="The user's location.")
    familial_genetic_diseases: Optional[str] = Field(
        None, description="The user's familial genetic diseases."
    )
    allergies: Optional[str] = Field(None, description="The user's allergies.")
    medications: Optional[str] = Field(None, description="The user's medications.")
    immunizations: Optional[str] = Field(None, description="The user's immunizations.")


class TeladocAccessUserInfoReturns(BaseModel):
    user_info: UserInfo = Field(
        ...,
        description="An object containing user information which may be sensitive, such as date of birth, location, familial genetic diseases, allergies, medications, and immunizations.",
    )


class HealthRecord(BaseModel):
    appointment_id: str = Field(
        ..., description="The unique identifier of the appointment."
    )
    date: str = Field(
        ..., description="The date of the medical record in the format 'YYYY-MM-DD'."
    )
    time: str = Field(
        ..., description="The time of the medical record in the format 'HH:mm'."
    )
    conclusions: str = Field(..., description="The conclusions of the medical record.")
    status: str = Field(..., description="The status of the medical record.")


class TeladocAccessMedicalHistoryReturns(BaseModel):
    health_records: List[HealthRecord] = Field(
        ...,
        description="A list of personal medical history, including appointment_id, date, time, conclusions, and status.",
    )


class TeladocRequestPrescriptionReturns(BaseModel):
    prescription_request_id: Optional[str] = Field(
        None,
        description="A unique identifier for the prescription request if successfully submitted, otherwise null.",
    )
    success: bool = Field(
        ...,
        description="A boolean indicating whether the prescription request was successfully submitted.",
    )


class Prescription(BaseModel):
    prescription_request_id: str = Field(
        ..., description="The unique identifier of the prescription request."
    )
    medication_name: str = Field(..., description="The name of the medication.")
    dosage: str = Field(..., description="The dosage of the medication.")
    status: str = Field(..., description="The status of the prescription.")
    doctor_id: str = Field(..., description="The unique identifier of the doctor.")


class TeladocViewPrescriptionsReturns(BaseModel):
    prescriptions: List[Prescription] = Field(
        ...,
        description="A list of prescriptions with their respective prescription_request_id, medication_name, dosage, status, and doctor_id.",
    )


class TeladocSendMessageReturns(BaseModel):
    doctor_response: str = Field(
        ..., description="The doctor's response to the sent message."
    )


class TeladocLeaveReviewReturns(BaseModel):
    success: bool = Field(
        ...,
        description="A boolean indicating whether the review was successfully posted.",
    )


class Review(BaseModel):
    reviewer_name: str = Field(..., description="The name of the reviewer.")
    rating: int = Field(..., description="The rating given by the reviewer (1-5).")
    review_content: str = Field(..., description="The content of the review.")


class TeladocViewReviewsReturns(BaseModel):
    reviews: List[Review] = Field(
        ...,
        description="A list of reviews for the doctor, each containing the reviewer's name, rating, and review content.",
    )


@register_toolkit_output_parser()
class TeladocOutputParser(ToolOutputParserCollection):
    name: str = Field(default="Teladoc")
    tool_name_to_output_parser: dict[str, Type[BaseModel]] = Field(
        default_factory=lambda: {
            "TeladocConsultDoctor": TeladocConsultDoctorReturns,
            "TeladocScheduleAppointment": TeladocScheduleAppointmentReturns,
            "TeladocManageAppointments": TeladocManageAppointmentsReturns,
            "TeladocAccessUserInfo": TeladocAccessUserInfoReturns,
            "TeladocAccessMedicalHistory": TeladocAccessMedicalHistoryReturns,
            "TeladocRequestPrescription": TeladocRequestPrescriptionReturns,
            "TeladocViewPrescriptions": TeladocViewPrescriptionsReturns,
            "TeladocSendMessage": TeladocSendMessageReturns,
            "TeladocLeaveReview": TeladocLeaveReviewReturns,
            "TeladocViewReviews": TeladocViewReviewsReturns,
        }
    )
