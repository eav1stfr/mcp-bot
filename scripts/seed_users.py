"""Create or update the two users and link them as partners.

Usage:
    uv run python -m scripts.seed_users \
        --user <telegram_id> <name> --user <telegram_id> <name>

Safe to run again: users are matched by Telegram ID, so a rerun only
renames them or fixes the partner link.
"""
import argparse

from sqlmodel import Session

from app.database import DB_ENGINE
from app.users.models import User
from app.users.repository import UserRepository


def parse_users(argv: list[str] | None = None) -> list[tuple[int, str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        nargs=2,
        action="append",
        required=True,
        metavar=("TELEGRAM_ID", "NAME"),
    )
    args = parser.parse_args(argv)

    users = [(int(telegram_id), name) for telegram_id, name in args.user]
    if len(users) != 2 or users[0][0] == users[1][0]:
        parser.error("pass --user exactly twice, with different Telegram IDs")
    return users


def upsert_user(repo: UserRepository, telegram_id: int, name: str) -> User:
    user = repo.get_by_telegram_id(telegram_id) or User(
        telegram_id=telegram_id, name=name
    )
    user.name = name
    return repo.update_without_commit(user)


def main(argv: list[str] | None = None) -> None:
    (first_id, first_name), (second_id, second_name) = parse_users(argv)

    with Session(DB_ENGINE) as session:
        repo = UserRepository(session)
        first = upsert_user(repo, first_id, first_name)
        second = upsert_user(repo, second_id, second_name)
        first.partner_id = second.id
        second.partner_id = first.id
        repo.update_without_commit(first)
        repo.update_without_commit(second)
        repo.commit()

        for user in (first, second):
            print(
                f"{user.name}: id={user.id}, telegram_id={user.telegram_id}, "
                f"partner_id={user.partner_id}"
            )


if __name__ == "__main__":
    main()
