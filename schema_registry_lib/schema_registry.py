from jsonschema import validate
import json
import os


class SchemaRegistry:
    def validate_event(self, data: dict, event_name: str, version: int):
        schema = self._get_schema(event_name, version)
        try:
            validate(instance=data, schema=schema)
        except Exception:
            return None
        return data

    def _get_schema(self, event_name: str, version: int):
        # event_name, Example - tasks.created
        current_dir = os.path.abspath(os.getcwd())

        domain, event = event_name.split('.')
        with open(f'{current_dir}/schemas/{domain}/{event}/{version}.json', 'r') as file:
            schema = json.load(file)
        return schema


if __name__ == '__main__':
    with open('schemas/tasks/created/1.json', 'r') as file:
        schema = json.load(file)
    validator = SchemaRegistry()
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
    validator.validate_event(test_data, 'tasks.created', 1)
