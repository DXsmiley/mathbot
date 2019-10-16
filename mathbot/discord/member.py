# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-2019 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import itertools
from operator import attrgetter

import discord.abc

from . import utils
from .user import BaseUser, User
from .activity import create_activity
from .permissions import Permissions
from .enums import Status, try_enum
from .colour import Colour
from .object import Object

class VoiceState:
    """Represents a Discord user's voice state.

    Attributes
    ------------
    deaf: :class:`bool`
        Indicates if the user is currently deafened by the guild.
    mute: :class:`bool`
        Indicates if the user is currently muted by the guild.
    self_mute: :class:`bool`
        Indicates if the user is currently muted by their own accord.
    self_deaf: :class:`bool`
        Indicates if the user is currently deafened by their own accord.
    self_stream: :class:`bool`
        Indicates if the user is currently streaming via 'Go Live' feature.

        .. versionadded:: 1.3.0 

    self_video: :class:`bool`
        Indicates if the user is currently broadcasting video.
    afk: :class:`bool`
        Indicates if the user is currently in the AFK channel in the guild.
    channel: :class:`VoiceChannel`
        The voice channel that the user is currently connected to. None if the user
        is not currently in a voice channel.
    """

    __slots__ = ('session_id', 'deaf', 'mute', 'self_mute',
                 'self_stream', 'self_video', 'self_deaf', 'afk', 'channel')

    def __init__(self, *, data, channel=None):
        self.session_id = data.get('session_id')
        self._update(data, channel)

    def _update(self, data, channel):
        self.self_mute = data.get('self_mute', False)
        self.self_deaf = data.get('self_deaf', False)
        self.self_stream = data.get('self_stream', False)
        self.self_video = data.get('self_video', False)
        self.afk = data.get('suppress', False)
        self.mute = data.get('mute', False)
        self.deaf = data.get('deaf', False)
        self.channel = channel

    def __repr__(self):
        return '<VoiceState self_mute={0.self_mute} self_deaf={0.self_deaf} self_stream={0.self_stream} channel={0.channel!r}>'.format(self)

def flatten_user(cls):
    for attr, value in itertools.chain(BaseUser.__dict__.items(), User.__dict__.items()):
        # ignore private/special methods
        if attr.startswith('_'):
            continue

        # don't override what we already have
        if attr in cls.__dict__:
            continue

        # if it's a slotted attribute or a property, redirect it
        # slotted members are implemented as member_descriptors in Type.__dict__
        if not hasattr(value, '__annotations__'):
            getter = attrgetter('_user.' + attr)
            setattr(cls, attr, property(getter, doc='Equivalent to :attr:`User.%s`' % attr))
        else:
            # Technically, this can also use attrgetter
            # However I'm not sure how I feel about "functions" returning properties
            # It probably breaks something in Sphinx.
            # probably a member function by now
            def generate_function(x):
                def general(self, *args, **kwargs):
                    return getattr(self._user, x)(*args, **kwargs)

                general.__name__ = x
                return general

            func = generate_function(attr)
            func.__doc__ = value.__doc__
            setattr(cls, attr, func)

    return cls

_BaseUser = discord.abc.User

@flatten_user
class Member(discord.abc.Messageable, _BaseUser):
    """Represents a Discord member to a :class:`Guild`.

    This implements a lot of the functionality of :class:`User`.

    .. container:: operations

        .. describe:: x == y

            Checks if two members are equal.
            Note that this works with :class:`User` instances too.

        .. describe:: x != y

            Checks if two members are not equal.
            Note that this works with :class:`User` instances too.

        .. describe:: hash(x)

            Returns the member's hash.

        .. describe:: str(x)

            Returns the member's name with the discriminator.

    Attributes
    ----------
    joined_at: Optional[:class:`datetime.datetime`]
        A datetime object that specifies the date and time in UTC that the member joined the guild for
        the first time. In certain cases, this can be ``None``.
    activities: Tuple[Union[:class:`Game`, :class:`Streaming`, :class:`Spotify`, :class:`Activity`]]
        The activities that the user is currently doing.
    guild: :class:`Guild`
        The guild that the member belongs to.
    nick: Optional[:class:`str`]
        The guild specific nickname of the user.
    premium_since: Optional[:class:`datetime.datetime`]
        A datetime object that specifies the date and time in UTC when the member used their
        Nitro boost on the guild, if available. This could be ``None``.
    """

    __slots__ = (
        '_roles',
        # 'joined_at',
        # 'premium_since',
        '_client_status',
        # 'activities',
        'guild',
        'nick',
        '_user',
        '_state'
    )

    def __init__(self, *, data, guild, state):
        self._state = state
        self._user = state.store_user(data['user'])
        self.guild = guild
        # self.joined_at = utils.parse_time(data.get('joined_at'))
        # self.premium_since = utils.parse_time(data.get('premium_since'))
        self._update_roles(data)
        self._client_status = {
            None: 'offline'
        }
        # self.activities = tuple(map(create_activity, data.get('activities', [])))
        self.nick = data.get('nick', None)

    def __str__(self):
        return str(self._user)

    def __repr__(self):
        return '<Member id={1.id} name={1.name!r} discriminator={1.discriminator!r}' \
               ' bot={1.bot} guild={0.guild!r}>'.format(self, self._user)

    def __eq__(self, other):
        return isinstance(other, _BaseUser) and other.id == self.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._user)

    @classmethod
    def _from_message(cls, *, message, data):
        author = message.author
        data['user'] = author._to_minimal_user_json()
        return cls(data=data, guild=message.guild, state=message._state)

    @classmethod
    def _try_upgrade(cls, *,  data, guild, state):
        # A User object with a 'member' key
        try:
            member_data = data.pop('member')
        except KeyError:
            return state.store_user(data)
        else:
            member_data['user'] = data
            return cls(data=member_data, guild=guild, state=state)

    @classmethod
    def _from_presence_update(cls, *, data, guild, state):
        clone = cls(data=data, guild=guild, state=state)
        to_return = cls(data=data, guild=guild, state=state)
        to_return._client_status = {
            key: value
            for key, value in data.get('client_status', {}).items()
        }
        to_return._client_status[None] = data['status']
        return to_return, clone

    @classmethod
    def _copy(cls, member):
        self = cls.__new__(cls) # to bypass __init__

        self._roles = utils.SnowflakeList(member._roles, is_sorted=True)
        # self.joined_at = member.joined_at
        # self.premium_since = member.premium_since
        self._client_status = member._client_status.copy()
        self.guild = member.guild
        self.nick = member.nick
        # self.activities = member.activities
        self._state = member._state

        # Reference will not be copied unless necessary by PRESENCE_UPDATE
        # See below
        self._user = member._user
        return self

    async def _get_channel(self):
        ch = await self.create_dm()
        return ch

    def _update_roles(self, data):
        self._roles = utils.SnowflakeList(map(int, data['roles']))

    def _update(self, data):
        # the nickname change is optional,
        # if it isn't in the payload then it didn't change
        try:
            self.nick = data['nick']
        except KeyError:
            pass

        # self.premium_since = utils.parse_time(data.get('premium_since'))
        self._update_roles(data)

    def _presence_update(self, data, user):
        # self.activities = tuple(map(create_activity, data.get('activities', [])))
        self._client_status = {
            key: value
            for key, value in data.get('client_status', {}).items()
        }
        self._client_status[None] = data['status']

        if len(user) > 1:
            u = self._user
            original = (u.name, u.discriminator)
            # These keys seem to always be available
            modified = (user['username'], user['discriminator'])
            if original != modified:
                to_return = User._copy(self._user)
                u.name, u.discriminator = modified
                # Signal to dispatch on_user_update
                return to_return, u
        return False

    @property
    def status(self):
        """:class:`Status`: The member's overall status. If the value is unknown, then it will be a :class:`str` instead."""
        return try_enum(Status, self._client_status[None])

    @status.setter
    def status(self, value):
        # internal use only
        self._client_status[None] = str(value)

    @property
    def mobile_status(self):
        """:class:`Status`: The member's status on a mobile device, if applicable."""
        return try_enum(Status, self._client_status.get('mobile', 'offline'))

    @property
    def desktop_status(self):
        """:class:`Status`: The member's status on the desktop client, if applicable."""
        return try_enum(Status, self._client_status.get('desktop', 'offline'))

    @property
    def web_status(self):
        """:class:`Status`: The member's status on the web client, if applicable."""
        return try_enum(Status, self._client_status.get('web', 'offline'))

    def is_on_mobile(self):
        """A helper function that determines if a member is active on a mobile device."""
        return 'mobile' in self._client_status

    # @property
    # def colour(self):
    #     """:class:`Colour`: A property that returns a colour denoting the rendered colour
    #     for the member. If the default colour is the one rendered then an instance
    #     of :meth:`Colour.default` is returned.

    #     There is an alias for this named :meth:`color`.
    #     """

    #     roles = self.roles[1:] # remove @everyone

    #     # highest order of the colour is the one that gets rendered.
    #     # if the highest is the default colour then the next one with a colour
    #     # is chosen instead
    #     for role in reversed(roles):
    #         if role.colour.value:
    #             return role.colour
    #     return Colour.default()

    # @property
    # def color(self):
    #     """:class:`Colour`: A property that returns a color denoting the rendered color for
    #     the member. If the default color is the one rendered then an instance of :meth:`Colour.default`
    #     is returned.

    #     There is an alias for this named :meth:`colour`.
    #     """
    #     return self.colour

    @property
    def roles(self):
        """List[:class:`Role`]: A :class:`list` of :class:`Role` that the member belongs to. Note
        that the first element of this list is always the default '@everyone'
        role.

        These roles are sorted by their position in the role hierarchy.
        """
        result = []
        g = self.guild
        for role_id in self._roles:
            role = g.get_role(role_id)
            if role:
                result.append(role)
        result.append(g.default_role)
        result.sort()
        return result

    @property
    def mention(self):
        """:class:`str`: Returns a string that allows you to mention the member."""
        if self.nick:
            return '<@!%s>' % self.id
        return '<@%s>' % self.id

    @property
    def display_name(self):
        """:class:`str`: Returns the user's display name.

        For regular users this is just their username, but
        if they have a guild specific nickname then that
        is returned instead.
        """
        return self.nick if self.nick is not None else self.name

    # @property
    # def activity(self):
    #     """Union[:class:`Game`, :class:`Streaming`, :class:`Spotify`, :class:`Activity`]: Returns the primary
    #     activity the user is currently doing. Could be None if no activity is being done.

    #     .. note::

    #         A user may have multiple activities, these can be accessed under :attr:`activities`.
    #     """
    #     if self.activities:
    #         return self.activities[0]

    def mentioned_in(self, message):
        """Checks if the member is mentioned in the specified message.

        Parameters
        -----------
        message: :class:`Message`
            The message to check if you're mentioned in.
        """
        if self._user.mentioned_in(message):
            return True

        for role in message.role_mentions:
            has_role = utils.get(self.roles, id=role.id) is not None
            if has_role:
                return True

        return False

    def permissions_in(self, channel):
        """An alias for :meth:`abc.GuildChannel.permissions_for`.

        Basically equivalent to:

        .. code-block:: python3

            channel.permissions_for(self)

        Parameters
        -----------
        channel: :class:`Channel`
            The channel to check your permissions for.
        """
        return channel.permissions_for(self)

    @property
    def top_role(self):
        """:class:`Role`: Returns the member's highest role.

        This is useful for figuring where a member stands in the role
        hierarchy chain.
        """
        return self.roles[-1]

    @property
    def guild_permissions(self):
        """Returns the member's guild permissions.

        This only takes into consideration the guild permissions
        and not most of the implied permissions or any of the
        channel permission overwrites. For 100% accurate permission
        calculation, please use either :meth:`permissions_in` or
        :meth:`abc.GuildChannel.permissions_for`.

        This does take into consideration guild ownership and the
        administrator implication.
        """

        if self.guild.owner_id == self.id:
            return Permissions.all()

        base = Permissions.none()
        for r in self.roles:
            base.value |= r.permissions.value

        if base.administrator:
            return Permissions.all()

        return base

    @property
    def voice(self):
        """Optional[:class:`VoiceState`]: Returns the member's current voice state."""
        return self.guild._voice_state_for(self._user.id)

    async def ban(self, **kwargs):
        """|coro|

        Bans this member. Equivalent to :meth:`Guild.ban`.
        """
        await self.guild.ban(self, **kwargs)

    async def unban(self, *, reason=None):
        """|coro|

        Unbans this member. Equivalent to :meth:`Guild.unban`.
        """
        await self.guild.unban(self, reason=reason)

    async def kick(self, *, reason=None):
        """|coro|

        Kicks this member. Equivalent to :meth:`Guild.kick`.
        """
        await self.guild.kick(self, reason=reason)

    async def edit(self, *, reason=None, **fields):
        """|coro|

        Edits the member's data.

        Depending on the parameter passed, this requires different permissions listed below:

        +---------------+--------------------------------------+
        |   Parameter   |              Permission              |
        +---------------+--------------------------------------+
        | nick          | :attr:`Permissions.manage_nicknames` |
        +---------------+--------------------------------------+
        | mute          | :attr:`Permissions.mute_members`     |
        +---------------+--------------------------------------+
        | deafen        | :attr:`Permissions.deafen_members`   |
        +---------------+--------------------------------------+
        | roles         | :attr:`Permissions.manage_roles`     |
        +---------------+--------------------------------------+
        | voice_channel | :attr:`Permissions.move_members`     |
        +---------------+--------------------------------------+

        All parameters are optional.

        .. versionchanged:: 1.1.0
            Can now pass ``None`` to ``voice_channel`` to kick a member from voice.

        Parameters
        -----------
        nick: Optional[:class:`str`]
            The member's new nickname. Use ``None`` to remove the nickname.
        mute: :class:`bool`
            Indicates if the member should be guild muted or un-muted.
        deafen: :class:`bool`
            Indicates if the member should be guild deafened or un-deafened.
        roles: Optional[List[:class:`Role`]]
            The member's new list of roles. This *replaces* the roles.
        voice_channel: Optional[:class:`VoiceChannel`]
            The voice channel to move the member to.
            Pass ``None`` to kick them from voice.
        reason: Optional[:class:`str`]
            The reason for editing this member. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have the proper permissions to the action requested.
        HTTPException
            The operation failed.
        """
        http = self._state.http
        guild_id = self.guild.id
        payload = {}

        try:
            nick = fields['nick']
        except KeyError:
            # nick not present so...
            pass
        else:
            nick = nick if nick else ''
            if self._state.self_id == self.id:
                await http.change_my_nickname(guild_id, nick, reason=reason)
            else:
                payload['nick'] = nick

        deafen = fields.get('deafen')
        if deafen is not None:
            payload['deaf'] = deafen

        mute = fields.get('mute')
        if mute is not None:
            payload['mute'] = mute

        try:
            vc = fields['voice_channel']
        except KeyError:
            pass
        else:
            payload['channel_id'] = vc and vc.id

        try:
            roles = fields['roles']
        except KeyError:
            pass
        else:
            payload['roles'] = tuple(r.id for r in roles)

        await http.edit_member(guild_id, self.id, reason=reason, **payload)

        # TODO: wait for WS event for modify-in-place behaviour

    async def move_to(self, channel, *, reason=None):
        """|coro|

        Moves a member to a new voice channel (they must be connected first).

        You must have the :attr:`~Permissions.move_members` permission to
        use this.

        This raises the same exceptions as :meth:`edit`.

        .. versionchanged:: 1.1.0
            Can now pass ``None`` to kick a member from voice.

        Parameters
        -----------
        channel: Optional[:class:`VoiceChannel`]
            The new voice channel to move the member to.
            Pass ``None`` to kick them from voice.
        reason: Optional[:class:`str`]
            The reason for doing this action. Shows up on the audit log.
        """
        await self.edit(voice_channel=channel, reason=reason)

    async def add_roles(self, *roles, reason=None, atomic=True):
        r"""|coro|

        Gives the member a number of :class:`Role`\s.

        You must have the :attr:`~Permissions.manage_roles` permission to
        use this.

        Parameters
        -----------
        \*roles: :class:`abc.Snowflake`
            An argument list of :class:`abc.Snowflake` representing a :class:`Role`
            to give to the member.
        reason: Optional[:class:`str`]
            The reason for adding these roles. Shows up on the audit log.
        atomic: :class:`bool`
            Whether to atomically add roles. This will ensure that multiple
            operations will always be applied regardless of the current
            state of the cache.

        Raises
        -------
        Forbidden
            You do not have permissions to add these roles.
        HTTPException
            Adding roles failed.
        """

        if not atomic:
            new_roles = utils._unique(Object(id=r.id) for s in (self.roles[1:], roles) for r in s)
            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.add_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, reason=reason)

    async def remove_roles(self, *roles, reason=None, atomic=True):
        r"""|coro|

        Removes :class:`Role`\s from this member.

        You must have the :attr:`~Permissions.manage_roles` permission to
        use this.

        Parameters
        -----------
        \*roles: :class:`abc.Snowflake`
            An argument list of :class:`abc.Snowflake` representing a :class:`Role`
            to remove from the member.
        reason: Optional[:class:`str`]
            The reason for removing these roles. Shows up on the audit log.
        atomic: :class:`bool`
            Whether to atomically remove roles. This will ensure that multiple
            operations will always be applied regardless of the current
            state of the cache.

        Raises
        -------
        Forbidden
            You do not have permissions to remove these roles.
        HTTPException
            Removing the roles failed.
        """

        if not atomic:
            new_roles = [Object(id=r.id) for r in self.roles[1:]] # remove @everyone
            for role in roles:
                try:
                    new_roles.remove(Object(id=role.id))
                except ValueError:
                    pass

            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.remove_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, reason=reason)
