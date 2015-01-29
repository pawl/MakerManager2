MakerManager2
---

An overhaul of the original MakerManager, written in Python: https://github.com/pawl/MakerManager

Improvements over MakerManager 1.0:
* Integration with Smartwaiver. If an admin or badge owner requests a badge and the person has signed a waiver - it will be activated automatically.
* A simpler and more maintainable codebase. It's written in Python instead of PHP. I'll post it on Github soon after I look it over a few times.
* A new status for "Lost" badges. This helps fix a bug that would activate all of an user's lost badges when they start their membership again.
* Now it sends an e-mail to the person who owns the badge that's being activated.
* The admin interface is much faster. It also has filters, pagination, and a search.
* Improved validation on the badge request form. Including a check for whether a duplicate badge is already active.
* A new "active badges" column to see who has too many badges activated.
* A new "badge activity" log that shows who deactivated/activated a badge and when.

TODO:
* Unit tests
* MenuLink items not showing as active when they are selected.
* Simplify the query in _get_filtered_list by using the ORM.
* Add filtering to "Total Products + Addons" and "Active Badges" columns on admin view.
* Allow deleting pending badges.
* Andrew wants to add a quiz for new members. Someone just needs to write the questions to it.
