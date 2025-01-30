from typeguard import typechecked


@typechecked
def uses_forwardref(x: NotYetDefined) -> NotYetDefined:
    return x


class NotYetDefined:
    pass
