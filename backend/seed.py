import asyncio
from datetime import date
from app.core.db import init_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.team import Team
from app.models.compliance_rule import ComplianceRule
from app.models.company import Company
from app.models.organization import Organization
from app.services.rule_engine import run_rule_engine_for_company

async def seed():
    print("Initializing database connection...")
    await init_db()
    
    # Check if database is already seeded
    existing_user = await User.find_one({"email": "admin@csdashboard.com"})
    if existing_user:
        print("Database already seeded. Skipping...")
        return

    print("Seeding users...")
    admin = User(
        email="admin@csdashboard.com",
        hashed_password=get_password_hash("Admin@123"),
        full_name="Admin Director",
        role="admin",
        is_active=True
    )
    staff1 = User(
        email="staff1@csdashboard.com",
        hashed_password=get_password_hash("Staff@123"),
        full_name="Rahul Sharma",
        role="staff",
        designation="executive",
        is_active=True
    )
    staff2 = User(
        email="staff2@csdashboard.com",
        hashed_password=get_password_hash("Staff@123"),
        full_name="Priya Patel",
        role="staff",
        designation="manager",
        is_active=True
    )
    partner = User(
        email="partner@csdashboard.com",
        hashed_password=get_password_hash("Partner@123"),
        full_name="Amit Verma",
        role="partner",
        is_active=True
    )
    ca_user = User(
        email="ca@csdashboard.com",
        hashed_password=get_password_hash("CA@123"),
        full_name="CA Harish Mehta",
        role="ca",
        is_active=True
    )
    await User.insert_many([admin, staff1, staff2, partner, ca_user])
    print("Seeding organization...")
    default_org = Organization(
        name="Default Firm",
        slug="default-firm"
    )
    await default_org.insert()

    # Assign users to the organization
    for user in (admin, staff1, staff2, partner, ca_user):
        user.organization_id = default_org.id
        await user.save()

    print("Seeding team...")
    default_team = Team(
        organization_id=default_org.id,
        name="Core Compliance Team",
        manager_id=staff2.id,
        member_ids=[staff1.id, staff2.id]
    )
    await default_team.insert()

    staff1.team_ids = [default_team.id]
    staff2.team_ids = [default_team.id]
    await staff1.save()
    await staff2.save()
    
    print("Seeding compliance rules...")
    rules = [
        # CS (ROC) Rules
        ComplianceRule(
            name="Annual Return Filing",
            form_number="MGT-7",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="annual",
            due_days_from_trigger=60,
            category="cs",
            description="Filing of annual return by a company contains information about shareholders, directors etc."
        ),
        ComplianceRule(
            name="Financial Statements Filing",
            form_number="AOC-4",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="annual",
            due_days_from_trigger=30,
            category="cs",
            description="Filing of financial statements, balance sheet, and profit & loss account."
        ),
        ComplianceRule(
            name="Particulars of Directors Appointment",
            form_number="DIR-12",
            company_types=["private_limited", "public_limited", "llp", "opc"],
            frequency="event_based",
            due_days_from_trigger=30,
            category="cs",
            description="Filing particulars of appointment of directors or change in designation."
        ),
        ComplianceRule(
            name="Resolutions Filing",
            form_number="MGT-14",
            company_types=["private_limited", "public_limited"],
            frequency="event_based",
            due_days_from_trigger=30,
            category="cs",
            description="Filing of board or general resolutions with the Registrar."
        ),
        ComplianceRule(
            name="Appointment of Auditor",
            form_number="ADT-1",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="annual",
            due_days_from_trigger=15,
            category="cs",
            description="Auditor appointment notice file with the ROC."
        ),
        ComplianceRule(
            name="Declaration of Commencement of Business",
            form_number="INC-20A",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="event_based",
            due_days_from_trigger=180,
            category="cs",
            description="Declaration of commencement of business after incorporation."
        ),
        ComplianceRule(
            name="Significant Beneficial Owners Declaration",
            form_number="BEN-2",
            company_types=["private_limited", "public_limited"],
            frequency="event_based",
            due_days_from_trigger=30,
            category="cs",
            description="Return to the Registrar in respect of declaration under Section 90."
        ),
        ComplianceRule(
            name="Return of Allotment of Shares",
            form_number="PAS-3",
            company_types=["private_limited", "public_limited"],
            frequency="event_based",
            due_days_from_trigger=30,
            category="cs",
            description="Filing return of share allotment details."
        ),
        ComplianceRule(
            name="Application for Charge Registration",
            form_number="CHG-1",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="event_based",
            due_days_from_trigger=30,
            category="cs",
            description="Application for registration of creation or modification of charge."
        ),
        ComplianceRule(
            name="LLP Annual Return Filing",
            form_number="LLP-8",
            company_types=["llp"],
            frequency="annual",
            due_days_from_trigger=30,
            category="cs",
            description="Filing of Statement of Account & Solvency for LLPs."
        ),
        
        # CA (Taxation & Auditing) Rules
        ComplianceRule(
            name="GST Return filing (Outward Supplies)",
            form_number="GSTR-1",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="monthly",
            due_days_from_trigger=11,
            category="ca",
            description="Monthly return of outward supplies (sales invoices) under GST."
        ),
        ComplianceRule(
            name="GST Summary Return (Payment & Credit)",
            form_number="GSTR-3B",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="monthly",
            due_days_from_trigger=20,
            category="ca",
            description="Self-declared monthly summary return with tax payments and Input Tax Credit (ITC) reconciliation."
        ),
        ComplianceRule(
            name="Annual GST Return",
            form_number="GSTR-9",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship"],
            frequency="annual",
            due_days_from_trigger=275,
            category="ca",
            description="Annual return compiling outward and inward supplies made during the financial year."
        ),
        ComplianceRule(
            name="Income Tax Return Filing",
            form_number="ITR-6",
            company_types=["private_limited", "public_limited", "opc"],
            frequency="annual",
            due_days_from_trigger=183,
            category="ca",
            description="Annual Income Tax Return (ITR) filing for corporate tax entities."
        ),
        ComplianceRule(
            name="Advance Tax 1st Installment",
            form_number="IT-ADV-1",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="quarterly",
            due_days_from_trigger=76,
            category="ca",
            description="First installment of advance tax (15% of total tax liability) due by June 15."
        ),
        ComplianceRule(
            name="Advance Tax 2nd Installment",
            form_number="IT-ADV-2",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="quarterly",
            due_days_from_trigger=168,
            category="ca",
            description="Second installment of advance tax (45% of total tax liability) due by September 15."
        ),
        ComplianceRule(
            name="Advance Tax 3rd Installment",
            form_number="IT-ADV-3",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="quarterly",
            due_days_from_trigger=259,
            category="ca",
            description="Third installment of advance tax (75% of total tax liability) due by December 15."
        ),
        ComplianceRule(
            name="Advance Tax 4th Installment",
            form_number="IT-ADV-4",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship", "individual"],
            frequency="quarterly",
            due_days_from_trigger=349,
            category="ca",
            description="Fourth installment of advance tax (100% of total tax liability) due by March 15."
        ),
        ComplianceRule(
            name="TDS Return (Quarterly Salary)",
            form_number="Form 24Q",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship"],
            frequency="quarterly",
            due_days_from_trigger=31,
            category="ca",
            description="Quarterly return for tax deducted at source from salaries."
        ),
        ComplianceRule(
            name="Tax Audit Statement of Particulars",
            form_number="Form 3CD",
            company_types=["private_limited", "public_limited", "llp", "opc", "partnership", "proprietorship"],
            frequency="annual",
            due_days_from_trigger=183,
            category="ca",
            description="Statement of particulars required to be furnished under section 44AB of the Income Tax Act."
        )
    ]
    await ComplianceRule.insert_many(rules)

    print("Seeding companies...")
    companies = [
        # CS-Only client
        Company(
            cin="U74140DL2015PTC288888",
            name="TechSolutions Private Limited",
            company_type="private_limited",
            reg_date=date(2015, 6, 12),
            financial_year_end=date(2026, 3, 31),
            address="102, Connaught Place, New Delhi - 110001",
            paid_up_capital=1500000.0,
            annual_turnover=5000000.0,
            bank_loan_amount=500000.0,
            assigned_to=staff1.id,
            client_type="cs",
            organization_id=default_org.id
        ),
        # CS-Only client
        Company(
            cin="U85110MH2020OPC345678",
            name="GlobalTrading OPC",
            company_type="opc",
            reg_date=date(2020, 10, 5),
            financial_year_end=date(2026, 3, 31),
            address="504, Nariman Point, Mumbai - 400021",
            assigned_to=staff2.id,
            client_type="cs",
            organization_id=default_org.id
        ),
        # BOTH client
        Company(
            cin="AAA-9999-LLP-INDIA-001",
            name="AlphaConsultants LLP",
            company_type="llp",
            reg_date=date(2018, 4, 1),
            financial_year_end=date(2026, 3, 31),
            address="Tower C, Tech Park, Bangalore - 560001",
            assigned_to=partner.id,
            pan="AAHCA5678K",
            gstin="29AAHCA5678K1ZA",
            client_type="both",
            organization_id=default_org.id
        ),
        # BOTH client
        Company(
            cin="U72200KA2021PTC142999",
            name="Sunshine Ventures Private Limited",
            company_type="private_limited",
            reg_date=date(2021, 2, 28),
            financial_year_end=date(2026, 3, 31),
            address="44, Koramangala, Bangalore - 560034",
            assigned_to=staff1.id,
            pan="AABCS1234M",
            gstin="29AABCS1234M2ZE",
            client_type="both",
            organization_id=default_org.id
        ),
        # CS-Only client
        Company(
            cin="L27100MH1998PLC115000",
            name="Apex Industries Public Limited",
            company_type="public_limited",
            reg_date=date(1998, 1, 15),
            financial_year_end=date(2026, 3, 31),
            address="MIDC Industrial Area, Pune - 411018",
            assigned_to=staff2.id,
            client_type="cs",
            organization_id=default_org.id
        ),
        # CA-Only client (Partnership)
        Company(
            name="Mehta & Sons Trading Co",
            company_type="partnership",
            reg_date=date(2019, 5, 20),
            financial_year_end=date(2026, 3, 31),
            address="72, Kalbadevi Road, Mumbai - 400002",
            assigned_to=ca_user.id,
            pan="AAAFM1111E",
            gstin="27AAAFM1111E1Z0",
            client_type="ca",
            organization_id=default_org.id
        ),
        # CA-Only client (Proprietorship)
        Company(
            name="Sharma Logistics & Transport",
            company_type="proprietorship",
            reg_date=date(2022, 1, 1),
            financial_year_end=date(2026, 3, 31),
            address="Plot 5, Transport Nagar, Jaipur - 302003",
            assigned_to=ca_user.id,
            pan="ABVPS5555L",
            gstin="08ABVPS5555L3ZG",
            client_type="ca",
            organization_id=default_org.id
        )
    ]
    await Company.insert_many(companies)
    
    print("Generating tasks for seeded companies...")
    for comp in companies:
        count = await run_rule_engine_for_company(None, comp, user_id=admin.id)
        print(f"Generated {count} compliance tasks for {comp.name}")
        
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
