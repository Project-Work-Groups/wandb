import json
from typing import Any, Dict, List, Optional, Union

import wandb
from wandb.apis.internal import Api
import wandb.apis.public as public
from wandb.sdk.launch.utils import construct_launch_spec


def push_to_queue(api: Api, queue: str, launch_spec: Dict[str, Any]) -> Any:
    try:
        res = api.push_to_run_queue(queue, launch_spec)
    except Exception as e:
        print("Exception:", e)
        return None
    return res


def launch_add(
    uri: Optional[str] = None,
    job: Optional[str] = None,
    config: Optional[Union[str, Dict[str, Any]]] = None,
    project: Optional[str] = None,
    entity: Optional[str] = None,
    queue: Optional[str] = None,
    resource: Optional[str] = None,
    entry_point: Optional[List[str]] = None,
    name: Optional[str] = None,
    version: Optional[str] = None,
    docker_image: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> "public.QueuedRun":

    api = Api()

    return _launch_add(
        api,
        uri,
        job,
        config,
        project,
        entity,
        queue,
        resource,
        entry_point,
        name,
        version,
        docker_image,
        params,
    )


def _launch_add(
    api: Api,
    uri: Optional[str],
    job: Optional[str],
    config: Optional[Union[str, Dict[str, Any]]],
    project: Optional[str],
    entity: Optional[str],
    queue: Optional[str],
    resource: Optional[str],
    entry_point: Optional[List[str]],
    name: Optional[str],
    version: Optional[str],
    docker_image: Optional[str],
    params: Optional[Dict[str, Any]],
    resource_args: Optional[Dict[str, Any]] = None,
    cuda: Optional[bool] = None,
) -> "public.QueuedRun":

    resource = resource or "local"
    if config is not None:
        if isinstance(config, str):
            with open(config) as fp:
                launch_config = json.load(fp)
        elif isinstance(config, dict):
            launch_config = config
    else:
        launch_config = {}

    if queue is None:
        queue = "default"

    launch_spec = construct_launch_spec(
        uri,
        job,
        api,
        name,
        project,
        entity,
        docker_image,
        resource,
        entry_point,
        version,
        params,
        resource_args,
        launch_config,
        cuda,
    )
    if (
        launch_spec.get("uri") is None
        and launch_spec.get("job") is None
        and launch_spec.get("docker", {}).get("docker_image") is None
    ):
        raise ValueError("Must specify either uri or job or docker_image")
    res = push_to_queue(api, queue, launch_spec)

    if res is None or "runQueueItemId" not in res:
        raise Exception("Error adding run to queue")
    wandb.termlog(f"Added run to queue {queue}")
    public_api = public.Api()
    queued_run_entity = launch_spec.get("entity")
    queued_run_project = launch_spec.get("project")
    queued_run = public_api.queued_run(
        f"{queued_run_entity}/{queued_run_project}/{queue}/{res['runQueueItemId']}"
    )
    return queued_run  # type: ignore
