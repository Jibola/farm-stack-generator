from __future__ import annotations
from motor.core import AgnosticDatabase
from beanie import WriteRules
from beanie.operators import And, In, PullAll

from app.crud.base import CRUDBase
from app.models import User, Token
from app.schemas import RefreshTokenCreate, RefreshTokenUpdate
from app.core.config import settings


class CRUDToken(CRUDBase[Token, RefreshTokenCreate, RefreshTokenUpdate]):
    # Everything is user-dependent
    async def create(self, db: AgnosticDatabase, *, obj_in: str, user_obj: User) -> Token:
        db_obj = await self.model.find_one(self.model.token == obj_in)
        if db_obj:
            if db_obj.authenticates_id != user_obj.id:
                raise ValueError("Token mismatch between key and user.")
            return db_obj
        else:
            new_token = self.model(token=obj_in, authenticates_id=user_obj.id)
            user_obj.refresh_tokens.append(new_token)
            await user_obj.save(link_rule=WriteRules.WRITE)
            return new_token

    async def get(self, *, user: User, token: str) -> Token:
        return await user.find_one(And(User.id == user.id, User.refresh_tokens.token == token), fetch_links=True)

    async def get_multi(self, *, user: User, page: int = 0, page_break: bool = False) -> list[Token]:
        offset = {"skip": page * settings.MULTI_MAX, "limit": settings.MULTI_MAX} if page_break else {}
        return await User.find(In(User.refresh_tokens, user.refresh_tokens), **offset).to_list()

    async def remove(self, db: AgnosticDatabase, *, db_obj: Token) -> None:
        await User.update_all(PullAll({User.refresh_tokens: [db_obj.to_ref()]}))
        await db_obj.delete()


token = CRUDToken(Token)
