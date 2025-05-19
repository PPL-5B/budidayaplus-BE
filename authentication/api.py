from authentication.schemas import LoginSchema, RegisterSchema, RefreshSchema
from authentication.services.auth_service import AuthenticationService
from ninja import Router
from ninja.throttling import AnonRateThrottle
from ninja_jwt.authentication import JWTAuth
from silk.profiling.profiler import silk_profile

router = Router()

@router.post("/login", throttle=AnonRateThrottle(rate="10/h"))
@silk_profile(name="Profiling Login API")
def login(request, data: LoginSchema):
    response = AuthenticationService.login(data.phone_number, data.password)
    return response

@router.post("/register")
def register(request, data: RegisterSchema):
    response = AuthenticationService.register(
        data.phone_number, data.first_name, data.last_name, data.password
    )
    return response

@router.post("/refresh")
def refresh(request, data: RefreshSchema):
    response = AuthenticationService.refresh_token(data.refresh)
    return response

@router.post("/validate", auth=JWTAuth())
def validate(request):
    response = AuthenticationService.validate_token(request.auth)
    return response

@router.get("/me", auth=JWTAuth())
def get_user_by_token(request):
    response = AuthenticationService.get_user_details(request.auth)
    return response