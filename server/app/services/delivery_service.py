from math import radians, cos, sin, asin, sqrt
from sqlalchemy.orm import Session
from app.models.driver import Driver
from app.services.driver_service import driver_can_take_a_job, restaurant_driver_filter

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # haversine formula 
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def assign_nearest_driver(db: Session, order_lat: float, order_lng: float, restaurant_id: str = None) -> Driver:
    """
    Find and return the nearest available driver for an order.
    """
    # Get all available drivers with location data
    available_drivers = db.query(Driver).filter(
        driver_can_take_a_job(),
        restaurant_driver_filter(restaurant_id),
        Driver.latitude.isnot(None),
        Driver.longitude.isnot(None)
    ).all()

    if not available_drivers:
        return None

    # Sort drivers by distance from order location
    drivers_with_distance = sorted(
        available_drivers,
        # the restaurant's own drivers before legacy shared ones, then by distance
        key=lambda d: (d.restaurant_id is None, haversine(order_lat, order_lng, d.latitude, d.longitude))
    )

    return drivers_with_distance[0]

def estimate_eta(distance_km: float, prep_minutes: int): # Default prep_minutes=30? No, let user pass it.
    """
    Estimate ETA based on distance and preparation time.
    Assuming average speed of 30km/h. 
    """
    driving_minutes = (distance_km / 30) * 60  # avg speed
    return int(prep_minutes + driving_minutes)
