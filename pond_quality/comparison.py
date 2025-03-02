# comparison.py

from fish_sampling.models import FishSampling
from pond_quality.models import PondQuality
from food_sampling.models import FoodSampling
from tasks.models import Task

def compare_ponds(selected_pond_id, cycle_id):
    selected_pond_data = {
        'fish_sampling': FishSampling.objects.filter(pond_id=selected_pond_id, cycle_id=cycle_id).latest('recorded_at'),
        'pond_quality': PondQuality.objects.filter(pond_id=selected_pond_id, cycle_id=cycle_id).latest('recorded_at'),
        'food_sampling': FoodSampling.objects.filter(pond_id=selected_pond_id, cycle_id=cycle_id).latest('recorded_at'),
        'task': Task.objects.filter(pond_id=selected_pond_id, cycle_id=cycle_id).latest('date')
    }
    
    other_ponds_data = []
    for pond in Pond.objects.exclude(pond_id=selected_pond_id):
        pond_data = {
            'fish_sampling': FishSampling.objects.filter(pond=pond, cycle_id=cycle_id).latest('recorded_at'),
            'pond_quality': PondQuality.objects.filter(pond=pond, cycle_id=cycle_id).latest('recorded_at'),
            'food_sampling': FoodSampling.objects.filter(pond=pond, cycle_id=cycle_id).latest('recorded_at'),
            'task': Task.objects.filter(pond=pond, cycle_id=cycle_id).latest('date')
        }
        other_ponds_data.append(pond_data)
    
    return selected_pond_data, other_ponds_data