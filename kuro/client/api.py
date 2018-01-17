import os
import coreapi


class Worker:
    def __init__(self, name, created_at, terminated):
        self.name = name
        self.created_at = created_at
        self.terminated = terminated


class KuroClient:
    def __init__(self, endpoint: str):
        self.schema_endpoint = os.path.join(endpoint, 'schema')
        self.client = coreapi.Client()
        self.schema = self.client.get(self.schema_endpoint)

    def list_workers(self):
        return [
            Worker(w['name'], w['created_at'], w['terminated'])
            for w in self.client.action(self.schema, ['workers', 'list'])
        ]

    def register_worker(self, name):
        worker = self.client.action(
            self.schema,
            ['workers', 'create'],
            params={'name': name}
        )
        return Worker(worker['name'], worker['created_at'], worker['terminated'])