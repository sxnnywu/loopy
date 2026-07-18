"""Reduce ~20k cortical vertices -> the 5 functional networks. Owner: B."""
NETWORKS = ["visual", "auditory", "language", "motion", "default_mode"]
def reduce_to_networks(vertex_timeseries) -> dict:
    raise NotImplementedError  # TODO(B): average vertices per network mask -> {name: [..]}
