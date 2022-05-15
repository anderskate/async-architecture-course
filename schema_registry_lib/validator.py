from jsonschema import validate
import json


class Validator:
    def validate(self, data, schema):
        validate(instance=data, schema=schema)
        return data


if __name__ == '__main__':
    with open('schemas/tasks/created/1.json', 'r') as file:
        schema = json.load(file)
    validator = Validator()
    test_data = {
        'event_name': 'task_created',
        'data': {
            'id': 40,
            'public_id': 'f8efdf1c-6698-4e33-b37b-e8901df3567e',
            'status': 'assigned',
            'description': 'test task 42424',
            'user_id': 5
        }
    }

    print(validator.validate(test_data, schema))