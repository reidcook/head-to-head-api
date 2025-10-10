# Helper to serialize MongoDB documents
def serialize_doc(doc):
    doc = dict(doc)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc