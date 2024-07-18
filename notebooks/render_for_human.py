from haicosystem.server import render_for_humans
from sotopia.database import EpisodeLog

episode = EpisodeLog.find(EpisodeLog.tag == "haicosystem_debug")[1]  # type: ignore
assert isinstance(episode, EpisodeLog)
render_for_humans(episode)
