from __future__ import annotations

import asyncio
import pytest
import pytest_asyncio

import sqlalchemy
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


from uno.auth.models import Customer, User, Group, Role, GroupPermission
from uno.enumerations import Permission
from config import settings


from contextlib import asynccontextmanager


@pytest_asyncio.fixture(scope="function")
async def async_session_generator():
    engine = create_async_engine(f"{settings.DB_URL}_test", echo=False)
    return sessionmaker(
        engine,
        class_=AsyncSession,
        # autoflush=False,
        expire_on_commit=False,
    )


@asynccontextmanager
@pytest_asyncio.fixture(scope="function")
async def async_session(async_session_generator):
    async with async_session_generator.begin() as async_session:
        await async_session.execute(
            text(
                f"""
                    SET session ROLE {settings.DB_SCHEMA}_writer;
                    SET session application_name = '{settings.SITE_NAME}';
                    SET session {settings.DB_SCHEMA}.user_id = 'ADMIN';
                """
            )
        )
        yield async_session
        try:
            await async_session.commit()
        except Exception:
            await async_session.close()


@pytest.mark.asyncio
async def test_create_customers(async_session):
    """Test creating customers.

    Creating a customer causes a trigger to create a group and role for the customer.
    Additionally, 8 group_permission records are created for each group, through a trigger
    on the group creation.
    The group_permission records are created with the following combinations of permissions:
        [READ]
        [READ, CREATE]
        [READ, CREATE, UPDATE]
        [READ, CREATE, DELETE]
        [READ, CREATE, UPDATE, DELETE]
        [READ, UPDATE]
        [READ, UPDATE, DELETE]
        [READ, DELETE]
    The role created is named "{customer_name} Admin", has the description "Admin Role", and has the
    group_permissions with [READ, CREATE, UPDATE, DELETE] for the group named [customer_name].
    Customers defined with the customer_type "INDIVIDUAL" do not have a group or role created.
    """
    customer_1 = Customer(name="Individual", customer_type="INDIVIDUAL")
    customer_2 = Customer(name="Small Business", customer_type="SMALL_BUSINESS")
    customer_3 = Customer(name="Corporate", customer_type="CORPORATE")
    customer_4 = Customer(name="Enterprise", customer_type="ENTERPRISE")

    async_session.add_all([customer_1, customer_2, customer_3, customer_4])
    await async_session.flush()

    group_count = await async_session.execute(select(func.count(Group.id)))
    assert group_count.scalar() == 4

    role_count = await async_session.execute(select(func.count(Role.id)))
    assert role_count.scalar() == 4

    group_permission_count = await async_session.execute(
        select(func.count(GroupPermission.id))
    )
    assert group_permission_count.scalar() == 32

    groups = await customer_1.awaitable_attrs.groups
    assert len(groups) == 1
    assert groups[0].__str__() == "Individual - Individual"

    customer_1.name = "Still an Individual"
    async_session.add(customer_1)
    await async_session.flush()

    customer_1.name = "Individual"
    async_session.add(customer_1)
    await async_session.flush()

    # Test creation of the group_permissions for customer_2
    groups = await customer_2.awaitable_attrs.groups

    customer_2_group_permissions_stmt = select(GroupPermission).where(
        GroupPermission.group_id == groups[0].id
    )
    customer_2_group_permissions = await async_session.scalars(
        customer_2_group_permissions_stmt
    )
    for gp in customer_2_group_permissions.all():
        if gp.name == "Read Only":
            assert gp.permissions == [Permission.READ]
            assert (
                gp.__str__()
                == "Small Business - Read Only - [<Permission.READ: 'Read'>]"
            )
        elif gp.name == "Read and Create":
            assert gp.permissions == [Permission.READ, Permission.CREATE]
        elif gp.name == "Read, Create, Update":
            assert gp.permissions == [
                Permission.READ,
                Permission.CREATE,
                Permission.UPDATE,
            ]
        elif gp.name == "Read, Create, Delete":
            assert gp.permissions == [
                Permission.READ,
                Permission.CREATE,
                Permission.DELETE,
            ]

        elif gp.name == "Admin":
            assert gp.permissions == [
                Permission.READ,
                Permission.CREATE,
                Permission.UPDATE,
                Permission.DELETE,
            ]
        elif gp.name == "Read and Update":
            assert gp.permissions == [Permission.READ, Permission.UPDATE]
        elif gp.name == "Read, Update, Delete":
            assert gp.permissions == [
                Permission.READ,
                Permission.UPDATE,
                Permission.DELETE,
            ]
        elif gp.name == "Read and Delete":
            assert gp.permissions == [Permission.READ, Permission.DELETE]
        else:
            assert False

    customer_0_first_role = await customer_2.awaitable_attrs.roles
    assert customer_0_first_role[0].name == "Small Business Admin"


@pytest.mark.asyncio
async def test_create_group_for_individual_exception(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Individual")
    )
    group_for_individual = Group(name="Individual Group", customer_id=customer.id)
    async_session.add(group_for_individual)
    with pytest.raises(Exception):
        await async_session.flush()


@pytest.mark.asyncio
async def test_create_group_for_small_business(async_session):
    # Get customer_2
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Small Business")
    )
    # Get the group with name "Small Business"
    group = await async_session.scalar(
        select(Group).filter(Group.name == "Small Business")
    )
    # Create two child groups of group
    group_2 = Group(
        name="Small Business Group 2", customer=customer, parent_id=group.id
    )
    group_3 = Group(
        name="Small Business Group 3", customer=customer, parent_id=group.id
    )
    async_session.add_all([group_2, group_3])
    await async_session.flush()
    # Create a child group of group_3
    group_4 = Group(
        name="Small Business Group 4", customer=customer, parent_id=group_3.id
    )
    async_session.add(group_4)
    await async_session.flush()
    # Create a child group of group_4
    group_5 = Group(
        name="Small Business Group 5", customer=customer, parent_id=group_4.id
    )
    async_session.add(group_5)
    await async_session.flush()
    # Get all the child groups of group
    child_groups = await async_session.scalars(
        text(f"SELECT auth.get_all_permissible_groups('{group.id}')")
    )
    for child_group in child_groups:
        assert child_group == [
            group.id,
            group_2.id,
            group_3.id,
            group_4.id,
            group_5.id,
        ]


@pytest.mark.asyncio
async def test_create_6th_group_for_small_business_exception(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Small Business")
    )
    # Create a child group of group_5
    group_6 = Group(name="Small Business Group 6", customer=customer)
    async_session.add(group_6)
    # Should raise an exception as the group_6 is the 6th group for a small business customer
    with pytest.raises(Exception):
        await async_session.flush()


@pytest.mark.asyncio
async def test_create_group_for_corporate(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Corporate")
    )
    for i in range(1, 25):
        group = Group(name=f"Corporate Group {i}", customer=customer)
        async_session.add(group)
        await async_session.flush()


@pytest.mark.asyncio
async def test_create_group_26_for_corporate_exception(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Corporate")
    )
    group = Group(name="Group 26", customer=customer)
    async_session.add(group)
    # Should raise an exception as the group is the 26th group for a corporate customer
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await async_session.flush()


@pytest.mark.asyncio
async def test_create_groups_for_enterprise(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Enterprise")
    )
    group = await async_session.scalar(
        select(Group).filter(
            Group.name == "Enterprise", Group.customer_id == customer.id
        )
    )
    for i in range(1, 101):
        group = Group(
            name=f"Enterprise Group {i}", customer=customer, parent_id=group.id
        )
        async_session.add(group)
        await async_session.flush()


@pytest.mark.asyncio
async def test_get_all_permissible_groups_for_enterprise(async_session):
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Enterprise")
    )
    group = await async_session.scalar(
        select(Group).filter(
            Group.name == "Enterprise", Group.customer_id == customer.id
        )
    )
    permissible_groups = await async_session.scalars(
        text(f"SELECT auth.get_all_permissible_groups('{group.id}')")
    )
    for permissible_group in permissible_groups:
        assert len(permissible_group) == 101


@pytest.mark.asyncio
async def test_create_users(async_session):
    customer_1 = await async_session.scalar(
        select(Customer).filter(Customer.name == "Individual")
    )
    customer_2 = await async_session.scalar(
        select(Customer).filter(Customer.name == "Small Business")
    )
    customer_3 = await async_session.scalar(
        select(Customer).filter(Customer.name == "Corporate")
    )
    customer_4 = await async_session.scalar(
        select(Customer).filter(Customer.name == "Enterprise")
    )

    user_0 = User(
        email="admin@notorm.tech",
        handle="@admin",
        full_name="Administrator",
        is_superuser=True,
    )
    user_1 = User(
        email="individual@individual.com",
        handle="@individual",
        full_name="Individual User",
        customer_id=customer_1.id,
    )
    user_2 = User(
        email="admin@customer2.com",
        handle="@admin_customer2",
        full_name="Admin Two",
        is_customer_admin=True,
        customer_id=customer_2.id,
    )
    user_3 = User(
        email="user1-2@customer2.com",
        handle="@user1-2",
        full_name="User One - Customer Two",
        customer_id=customer_2.id,
    )
    user_4 = User(
        email="user2-2@customer2.com",
        handle="@user2-2",
        full_name="User Two - Customer Two",
        customer_id=customer_2.id,
    )
    user_5 = User(
        email="admin@customer3.com",
        handle="@admin_customer3",
        full_name="Admin Three",
        is_customer_admin=True,
        customer_id=customer_3.id,
    )
    user_6 = User(
        email="user1-3@customer3.com",
        handle="@user1-3",
        full_name="User One - Customer Three",
        customer_id=customer_3.id,
    )
    user_7 = User(
        email="user2-3@customer3.com",
        handle="@user2-3",
        full_name="User Two - Customer Three",
        customer_id=customer_3.id,
    )
    user_8 = User(
        email="user3-3@customer3.com",
        handle="@user3-3",
        full_name="User Three - Customer Three",
        customer_id=customer_3.id,
    )
    user_9 = User(
        email="admin@customer4.com",
        handle="@admin_customer4",
        full_name="Admin Four",
        is_customer_admin=True,
        customer_id=customer_4.id,
    )
    user_10 = User(
        email="user1-4@customer4.com",
        handle="@user1-4",
        full_name="User One - Customer Four",
        customer_id=customer_4.id,
    )
    user_11 = User(
        email="user2-4@customer4.com",
        handle="@user2-4",
        full_name="User Two - Customer Four",
        customer_id=customer_4.id,
    )
    user_12 = User(
        email="user3-4@customer4.com",
        handle="@user3-4",
        full_name="User Three - Customer Four",
        customer_id=customer_4.id,
    )
    user_13 = User(
        email="user4-4@customer4.com",
        handle="@user4-4",
        full_name="User Four - Customer Four",
        customer_id=customer_4.id,
    )
    user_14 = User(
        email="user5-4@customer4.com",
        handle="@user5-4",
        full_name="User Five - Customer Four",
        customer_id=customer_4.id,
    )
    async_session.add_all(
        [
            user_0,
            user_1,
            user_2,
            user_3,
            user_4,
            user_5,
            user_6,
            user_7,
            user_8,
            user_9,
            user_10,
            user_11,
            user_12,
            user_13,
            user_14,
        ]
    )
    await async_session.flush()
    customer_2_admin_role = await async_session.scalar(
        select(Role).where(
            Role.customer_id == customer_2.id,
            Role.name == "Small Business Admin",
        )
    )
    user_2_roles = await user_2.awaitable_attrs.roles
    user_2_roles.append(customer_2_admin_role)
    async_session.add(user_2)
    await async_session.flush()


@pytest.mark.asyncio
async def test_create_superuser_with_customer_exception(async_session):
    """Ensure that a user cannot be created with is_superuser = True if they are associated with a customer."""
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Enterprise")
    )

    user_0 = User(
        email="admin1@notorm.tech",
        handle="@admin1",
        full_name="Administrator1",
        is_superuser=True,
        customer_id=customer.id,
    )
    async_session.add(user_0)
    with pytest.raises(Exception):
        await async_session.flush()


@pytest.mark.asyncio
async def test_update_superuser_with_customer_exception(async_session):
    """Ensuer that a user cannot be updated to have a customer_id if they are a superuser."""
    customer = await async_session.scalar(
        select(Customer).filter(Customer.name == "Enterprise")
    )
    user = await async_session.scalar(
        select(User).filter(User.email == "admin@notorm.tech")
    )
    user.customer = customer
    async_session.add(user)
    with pytest.raises(Exception):
        await async_session.flush()


@pytest.mark.asyncio
async def test_update_unpriviled_user_with_is_superuser_exception(async_session):
    """Ensure that a user cannot be updated to have is_superuser = True if they are associated with a customer"""
    user = await async_session.scalar(
        select(User).filter(User.email == "user5-4@customer4.com")
    )
    user.is_superuser = True
    async_session.add(user)
    with pytest.raises(Exception):
        await async_session.flush()


@pytest.mark.asyncio
async def test_update__user_with_is_superuser_exception(async_session):
    """Ensure that a user cannot be updated to have is_superuser = True if they are associated with a customer"""
    user = await async_session.scalar(
        select(User).filter(User.email == "user5-4@customer4.com")
    )
    user.is_superuser = True
    async_session.add(user)
    with pytest.raises(Exception):
        await async_session.flush()
