
from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union
import logging
from swarms.structs.flow import Flow


from swarms import Flow, OpenAI

logger = logging.getLogger(__name__)


@dataclass
class GroupChat:
    """A group chat class that contains a list of agents and the maximum number of rounds."""

    agents: List[Flow]
    messages: List[Dict]
    max_round: int = 10
    admin_name: str = "Admin"  # the name of the admin agent

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def agent_by_name(self, name: str) -> Flow:
        """Find an agent whose name is contained within the given 'name' string."""
        for agent in self.agents:
            if agent.name in name:
                return agent
        raise ValueError(f"No agent found with a name contained in '{name}'.")

    def next_agent(self, agent: Flow) -> Flow:
        """Return the next agent in the list."""
        return self.agents[(self.agent_names.index(agent.name) + 1) % len(self.agents)]

    def select_speaker_msg(self):
        """Return the message for selecting the next speaker."""

        return f"""
        You are in a role play game. The following roles are available:
        {self._participant_roles()}.

        Read the following conversation.
        Then select the next role from {self.agent_names} to play. Only return the role.
        """


    def select_speaker(self, last_speaker: Flow, selector: Flow):
        """Select the next speaker."""
        selector.update_system_message(self.select_speaker_msg())

        # Warn if GroupChat is underpopulated, without established changing behavior
        n_agents = len(self.agent_names)
        if n_agents < 3:
            logger.warning(
                f"GroupChat is underpopulated with {n_agents} agents. Direct communication would be more efficient."
            )

        name = selector.generate_reply(

            self.format_history(
                self.messages
                + [
                    {
                        "role": "system",
                        "content": f"Read the above conversation. Then select the next most suitable role from {self.agent_names} to play. Only return the role.",
                    }
                ]
            )
        )
        try:
            return self.agent_by_name(name["content"])
        except ValueError:
            return self.next_agent(last_speaker)

    def _participant_roles(self):

        return "\n".join(
            [f"{agent.name}: {agent.system_message}" for agent in self.agents]
        )


    def format_history(self, messages: List[Dict]) -> str:
        formatted_messages = []
        for message in messages:
            formatted_message = f"'{message['role']}:{message['content']}"
            formatted_messages.append(formatted_message)
        return "\n".join(formatted_messages)



class GroupChatManager:
    def __init__(self, groupchat: GroupChat, selector: Flow):
        self.groupchat = groupchat
        self.selector = selector

    def __call__(self, task: str):
        self.groupchat.messages.append({"role": self.selector.name, "content": task})
        for i in range(self.groupchat.max_round):
            speaker = self.groupchat.select_speaker(
                last_speaker=self.selector, selector=self.selector
            )
            reply = speaker.generate_reply(
                self.groupchat.format_history(self.groupchat.messages)
            )
            self.groupchat.messages.append(reply)
            print(reply)
            if i == self.groupchat.max_round - 1:
                break

        return reply

