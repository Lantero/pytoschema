import typing

ServicePort = typing.Union[int, float]
ServiceConfig = typing.Dict[str, typing.Any]
ServiceState = typing.Literal["RUNNING", "STOPPED", "UNKNOWN"]


class Service(typing.TypedDict, total=False):
    address: str
    port: ServicePort
    config: ServiceConfig
    state: ServiceState
    tags: typing.List[str]
    debug: bool
