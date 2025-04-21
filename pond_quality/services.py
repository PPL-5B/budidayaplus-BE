from typing import Optional
from pond_quality.models import PondQuality
from pond.models import Pond
from cycle.models import Cycle


def get_pond_qualities_for_response(cycle: Cycle, pond: Pond, limit: Optional[int] = 10):
    #Mengambil data pond quality berdasarkan cycle dan pond tertentu.
    #Menggunakan select_related agar efisien dan menghindari N+1 query.
    return PondQuality.objects.filter(
        cycle=cycle,
        pond=pond
    ).select_related(
        "reporter", "pond", "cycle"
    ).order_by("-recorded_at")[:limit]


def fetch_latest_pond_quality(cycle: Cycle, pond: Pond):
    """
    Mengambil satu data pond quality terakhir untuk pond dan cycle tertentu.
    Sudah include select_related.
    """
    return PondQuality.objects.filter(
        cycle=cycle,
        pond=pond
    ).select_related("reporter", "pond", "cycle").latest("recorded_at")
