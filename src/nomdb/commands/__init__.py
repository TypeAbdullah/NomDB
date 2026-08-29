"""
NomDB Commands Package and default registry loader.
"""

from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.commands.registry import CommandRegistry

# String commands
from nomdb.commands.strings import (
    SetCommand,
    GetCommand,
    GetDelCommand,
    GetExCommand,
    GetSetCommand,
    MGetCommand,
    MSetCommand,
    SetNxCommand,
    IncrCommand,
    IncrByCommand,
    IncrByFloatCommand,
    DecrCommand,
    DecrByCommand,
    AppendCommand,
    StrLenCommand,
    SetRangeCommand,
    GetRangeCommand,
)

# Hash commands
from nomdb.commands.hashes import (
    HSetCommand,
    HGetCommand,
    HMGetCommand,
    HDelCommand,
    HExistsCommand,
    HGetAllCommand,
    HKeysCommand,
    HValsCommand,
    HLenCommand,
    HIncrByCommand,
    HIncrByFloatCommand,
    HSetNxCommand,
)

# List commands
from nomdb.commands.lists import (
    LPushCommand,
    RPushCommand,
    LPopCommand,
    RPopCommand,
    LRangeCommand,
    LLenCommand,
    LIndexCommand,
    LSetCommand,
    LInsertCommand,
    LTrimCommand,
    LRemCommand,
)

# Set commands
from nomdb.commands.sets import (
    SAddCommand,
    SRemCommand,
    SIsMemberCommand,
    SMIsMemberCommand,
    SMembersCommand,
    SCardCommand,
    SPopCommand,
    SRandMemberCommand,
    SUnionCommand,
    SInterCommand,
    SDiffCommand,
)

# Sorted set commands
from nomdb.commands.sorted_sets import (
    ZAddCommand,
    ZRemCommand,
    ZScoreCommand,
    ZRankCommand,
    ZRevRankCommand,
    ZRangeCommand,
    ZRevRangeCommand,
    ZCardCommand,
    ZCountCommand,
    ZIncrByCommand,
)

# Key management commands
from nomdb.commands.keys import (
    DelCommand,
    ExistsCommand,
    ExpireCommand,
    PExpireCommand,
    ExpireAtCommand,
    PExpireAtCommand,
    TtlCommand,
    PTtlCommand,
    PersistCommand,
    TypeCommand,
    RenameCommand,
    RenameNxCommand,
    KeysCommand,
    ScanCommand,
    DBSizeCommand,
    RandomKeyCommand,
    FlushDBCommand,
    FlushAllCommand,
    SelectCommand,
)

# Server commands
from nomdb.commands.server import (
    PingCommand,
    EchoCommand,
    InfoCommand,
    ConfigGetCommand,
    TimeCommand,
    CommandCommand,
    SaveCommand,
    BgSaveCommand,
    ShutdownCommand,
    AuthCommand,
    MemoryCommand,
    QuitCommand,
)

# Transaction commands
from nomdb.commands.transactions import (
    MultiCommand,
    ExecCommand,
    DiscardCommand,
    WatchCommand,
    UnwatchCommand,
)

# Pub/Sub commands
from nomdb.commands.pubsub import (
    SubscribeCommand,
    UnsubscribeCommand,
    PSubscribeCommand,
    PUnsubscribeCommand,
    PublishCommand,
)

# Replication commands
from nomdb.commands.replication import (
    ReplConfCommand,
    PSyncCommand,
    SyncCommand,
    ReplicaOfCommand,
    SlaveOfCommand,
)

# Cluster commands
from nomdb.commands.cluster import ClusterCommand


def create_default_registry() -> CommandRegistry:
    """Instantiate and register all built-in NomDB commands."""
    registry = CommandRegistry()

    commands = [
        # Strings
        SetCommand(),
        GetCommand(),
        GetDelCommand(),
        GetExCommand(),
        GetSetCommand(),
        MGetCommand(),
        MSetCommand(),
        SetNxCommand(),
        IncrCommand(),
        IncrByCommand(),
        IncrByFloatCommand(),
        DecrCommand(),
        DecrByCommand(),
        AppendCommand(),
        StrLenCommand(),
        SetRangeCommand(),
        GetRangeCommand(),
        # Hashes
        HSetCommand(),
        HGetCommand(),
        HMGetCommand(),
        HDelCommand(),
        HExistsCommand(),
        HGetAllCommand(),
        HKeysCommand(),
        HValsCommand(),
        HLenCommand(),
        HIncrByCommand(),
        HIncrByFloatCommand(),
        HSetNxCommand(),
        # Lists
        LPushCommand(),
        RPushCommand(),
        LPopCommand(),
        RPopCommand(),
        LRangeCommand(),
        LLenCommand(),
        LIndexCommand(),
        LSetCommand(),
        LInsertCommand(),
        LTrimCommand(),
        LRemCommand(),
        # Sets
        SAddCommand(),
        SRemCommand(),
        SIsMemberCommand(),
        SMIsMemberCommand(),
        SMembersCommand(),
        SCardCommand(),
        SPopCommand(),
        SRandMemberCommand(),
        SUnionCommand(),
        SInterCommand(),
        SDiffCommand(),
        # Sorted Sets
        ZAddCommand(),
        ZRemCommand(),
        ZScoreCommand(),
        ZRankCommand(),
        ZRevRankCommand(),
        ZRangeCommand(),
        ZRevRangeCommand(),
        ZCardCommand(),
        ZCountCommand(),
        ZIncrByCommand(),
        # Keys
        DelCommand(),
        ExistsCommand(),
        ExpireCommand(),
        PExpireCommand(),
        ExpireAtCommand(),
        PExpireAtCommand(),
        TtlCommand(),
        PTtlCommand(),
        PersistCommand(),
        TypeCommand(),
        RenameCommand(),
        RenameNxCommand(),
        KeysCommand(),
        ScanCommand(),
        DBSizeCommand(),
        RandomKeyCommand(),
        FlushDBCommand(),
        FlushAllCommand(),
        SelectCommand(),
        # Server
        PingCommand(),
        EchoCommand(),
        InfoCommand(),
        ConfigGetCommand(),
        TimeCommand(),
        CommandCommand(),
        SaveCommand(),
        BgSaveCommand(),
        ShutdownCommand(),
        AuthCommand(),
        MemoryCommand(),
        QuitCommand(),
        # Transactions
        MultiCommand(),
        ExecCommand(),
        DiscardCommand(),
        WatchCommand(),
        UnwatchCommand(),
        # Pub/Sub
        SubscribeCommand(),
        UnsubscribeCommand(),
        PSubscribeCommand(),
        PUnsubscribeCommand(),
        PublishCommand(),
        # Replication
        ReplConfCommand(),
        PSyncCommand(),
        SyncCommand(),
        ReplicaOfCommand(),
        SlaveOfCommand(),
        # Cluster
        ClusterCommand(),
    ]

    for cmd in commands:
        registry.register(cmd)

    return registry
