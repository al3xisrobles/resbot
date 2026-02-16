import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

# Clear cache for Monkey Bar (60058) and Carbone (6194)
venues_to_clear = ['60058', '6194']

for venue_id in venues_to_clear:
    doc_ref = db.collection('venues').document(venue_id)
    doc = doc_ref.get()
    if doc.exists:
        doc_ref.delete()
        print(f"Deleted cache for venue {venue_id}")
    else:
        print(f"No cache found for venue {venue_id}")

print("Done!")
