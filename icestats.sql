drop table if exists listeners;
create table listeners (
    id integer primary key,
    ip text not null,
    start integer not null,
    stop integer not null,
    length integer,
    mount text,
    referrer text,
    agent text
    );

