import json
from collections.abc import Callable

import luigi
import luigi.freezing
import luigi.util

from loading_pipeline.lib.misc.validation import SeqrValidationError
from loading_pipeline.lib.paths import validation_errors_for_run_path
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.files import GCSorLocalTarget


def _deep_merge_dicts(existing: dict, new: dict) -> dict:
    """Recursively merge new dict into existing dict."""
    result = existing.copy()
    for key, new_value in new.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(new_value, dict)
        ):
            result[key] = _deep_merge_dicts(result[key], new_value)
        else:
            result[key] = new_value
    return result


@luigi.util.inherits(BaseLoadingRunParams)
class UpdatedValidationErrorsForRunTask(luigi.Task):
    project_guids = luigi.ListParameter()
    error_messages = luigi.ListParameter(default=[])
    error_body = luigi.DictParameter(default={})

    def complete(self) -> bool:
        """Check if all input project_guids and error_messages are contained in the output."""
        output_path = self.output()
        if not output_path.exists():
            return False

        with output_path.open('r') as f:
            data = json.load(f)

        output_project_guids = set(data.get('project_guids', []))
        output_error_messages = set(data.get('error_messages', []))

        input_project_guids = set(self.project_guids)
        input_error_messages = set(self.error_messages)

        # Check if all input items are in output
        return input_project_guids.issubset(
            output_project_guids,
        ) and input_error_messages.issubset(output_error_messages)

    def to_single_error_message(self) -> str:
        with self.output().open('r') as f:
            error_messages = json.load(f)['error_messages']
            if len(error_messages) == 1:
                return error_messages[0]
            return f'Multiple validation errors encountered: {error_messages}'

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            validation_errors_for_run_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def run(self) -> None:
        output_path = self.output()

        # Load existing data if file exists
        existing_data = {}
        if output_path.exists():
            with output_path.open('r') as f:
                existing_data = json.load(f)

        # Append new project_guids to existing ones and deduplicate while preserving order
        project_guids = list(
            dict.fromkeys(
                existing_data.get('project_guids', []) + list(self.project_guids),
            ),
        )

        # Append new error_messages to existing ones and deduplicate while preserving order
        error_messages = list(
            dict.fromkeys(
                existing_data.get('error_messages', []) + list(self.error_messages),
            ),
        )

        # Merge error_body with new data recursively
        error_body = _deep_merge_dicts(
            {
                k: v
                for k, v in existing_data.items()
                if k not in ('project_guids', 'error_messages')
            },
            luigi.freezing.recursively_unfreeze(self.error_body),
        )

        validation_errors_json = {
            'project_guids': project_guids,
            'error_messages': error_messages,
            **error_body,
        }
        with output_path.open('w') as f:
            json.dump(validation_errors_json, f)


def with_persisted_validation_errors(f: Callable) -> Callable[[Callable], Callable]:
    def wrapper(self: luigi.Task):
        try:
            return f(self)
        except SeqrValidationError as e:
            updated_validation_errors_for_run_task = self.clone(
                UpdatedValidationErrorsForRunTask,
                error_messages=[e.msg],
                error_body=e.error_body,
            )
            updated_validation_errors_for_run_task.run()
            raise SeqrValidationError(
                updated_validation_errors_for_run_task.to_single_error_message(),
            ) from None

    return wrapper
