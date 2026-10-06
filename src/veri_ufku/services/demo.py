"""Infrastructure use cases; not analytics or a dataset importer."""

from veri_ufku.domain.contracts import Binding, DemoParameters, JobSpec


class DemoSession:
    def __init__(self, manager, budget):
        self.manager = manager
        self.budget = budget
        self.binding = Binding("demo-session:v1", 0)

    def start(self, capability_id):
        return self.manager.submit(
            JobSpec(capability_id, self.binding, DemoParameters(), self.budget)
        )

    def change_configuration(self):
        self.binding = Binding(
            self.binding.dataset_version, self.binding.config_revision + 1
        )
