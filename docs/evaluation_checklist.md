# Evaluation Checklist

## Mid-semester
- [ ] Replace team placeholders with actual names and IDs.
- [ ] Add actual contribution breakdown to README.
- [ ] Review problem statement, users, assumptions and business rules.
- [ ] Render and validate `ERD.mmd`.
- [ ] Run `sql/schema.sql` on PostgreSQL 15+.
- [ ] Explain each PK/FK/UNIQUE/CHECK constraint and index.
- [ ] Explain `[start,end)` reservation ranges and exclusion constraint.
- [ ] Explain 1NF/2NF/3NF and tariff snapshot.
- [ ] Submit the <=5-page design PDF, application architecture/workflows and GitHub URL.

## Final
- [ ] Complete driver vehicle/history/invoice UI.
- [ ] Complete operator session start/end and invoice generation UI.
- [ ] Add simulated payment UI and operational reports.
- [ ] Validate vehicle ownership, connector compatibility, port status and tariff validity.
- [ ] Prevent payments exceeding outstanding balances.
- [ ] Add authentication/role access if required.
- [ ] Test overlap conflict, rollback, invalid meter values, duplicate invoices and payment status.
- [ ] Load and verify 500+ synthetic rows.
- [ ] Demonstrate 3+ end-to-end workflows, 5+ non-trivial SQL queries and 3+ DBMS features.
- [ ] Verify clean setup from README and ensure every member can explain the design.
