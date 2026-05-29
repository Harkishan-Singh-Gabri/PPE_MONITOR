import numpy as np
def calculate_angle(a,b,c):
    """
    angle at point B formed by A->B->C
    a,b,c are dicts with 'x' and 'y' keys
    returns angle in degrees
    """
    a=np.array([a['x'], a['y']])
    b=np.array([b['x'], b['y']])
    c=np.array([c['x'], c['y']])

    ba=a-b
    bc=c-b

    cosine=np.dot(ba,bc)/ (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle=np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
    return round(float(angle), 1)

def midpoint(a,b):
    return{
        'x': (a['x'] + b['x'])/2,
        'y': (a['y'] + b['y'])/2
    }

def is_visible(*landmarks, threshold=0.5):
    """Check if all given landmarks are visible enough."""
    for lm in landmarks:
        if lm is None:
            return False
        if isinstance(lm, dict) and lm.get("visibility", 0) < threshold:
            return False
    return True


