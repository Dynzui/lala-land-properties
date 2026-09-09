# Lala Land Properties CMS Guide

This guide explains the administration area at `/admin/` in everyday language. It is written for Lala and future staff members.

## 1. Signing in and account safety

1. Open the website's `/admin/` address.
2. Enter your own username and password.
3. Complete two-factor authentication when requested.
4. Keep the recovery codes somewhere private and offline. Each code is for emergencies and should not be shared with an Admin or Maintainer.
5. Sign out when using a shared computer.

Never share the Owner account. Give each employee a separate account so the audit log can show who performed an action.

### Account roles

- **Owner:** Lala's highest-level account. It manages staff, private information, audit history, listings, inquiries, articles, and site content.
- **Admin:** Day-to-day business staff. Admins can manage properties, listings, inquiries, and articles. They need Owner approval to view customer phone numbers or exact private locations.
- **Maintainer:** Technical maintenance only. This role cannot use the business CMS or bypass the Owner's authentication.
- **Customer:** Public website account level. It cannot enter the CMS.

## 2. Adding and editing a property listing

Use **Listings** in the main sidebar. Select **Add property listing** and complete the five sections. This one guided form creates the internal Property, Listing, and Price and availability records together.

Choose **One specific property or lot** for resale homes, individual rentals, specific lots, and most everyday listings. Choose **Several interchangeable units of one house model** only when multiple units share the same design and one listing represents the whole pool.

If the needed Location, Development, or House model does not exist yet, use the shortcut at the top of the form to create it, then return to Listings. After saving, use **Add photos** beside the listing. Review the draft and select **Publish** only when it is ready.

To make changes later, select **Edit listing**. The same guided form updates the public copy, property details, availability, and price without creating replacement records.

## 3. Advanced catalogue records

The technical Snippets menu is intentionally hidden from the main sidebar. The following records remain available through the guided Listings and Developments screens when advanced maintenance is needed.

### Property types

Examples include House and Lot, Condominium, Lot, Commercial Property, Apartment, or Memorial Lot.

- **Name:** The label staff and customers see.
- **Slug:** A short URL-friendly value, normally lowercase with hyphens, such as `house-and-lot`.
- **Description:** An internal or public explanation of the type.
- **Applicable fields:** Select only the details that make sense, such as bedrooms, floor area, or memorial capacity.
- **Sort order:** Lower numbers appear first.
- **Active:** Turn this off to prevent the type from being used for new records. Deactivate instead of deleting a type already in use.

### Locations

Locations separate public information from the exact private address.

- **Region, Province, City/Municipality, and Barangay:** Select the official Philippine area values.
- **Subdivision/Area:** Optional neighborhood or development-area name.
- **Public label:** The visitor-friendly wording, such as `Bacolod City, Negros Occidental`.
- **Visibility:** Controls what customers can see.
  - **Exact public pin:** Shows the chosen public pin precisely.
  - **Approximate public pin:** Shows a general public pin, not the property's exact private position.
  - **Area label only:** Shows text only and no map pin. This is the safest normal choice.
  - **Hidden:** Hides the location from public listing output and prevents publication until corrected.
- **Public map pin:** Click the map to select the location visitors are allowed to see.
- **Private exact address and pin:** Owner-only information. Use the private map for the real location when needed.

An Admin cannot see private address fields by default. They must request temporary access from the Owner. The Owner may approve, deny, or revoke that access.

The Owner can delete an unused Location. If other records depend on it, keep it rather than breaking the catalogue.

### Developments

A Development is a larger project containing one or more variants or individual properties.

- **Name and slug:** Public name and URL-friendly identifier.
- **Development type:** Subdivision, condominium, commercial, memorial park, mixed use, or other.
- **Location:** Select an existing Location.
- **Summary and description:** Short preview text and full details.
- **Developer name:** Optional developer or company.
- **Status:**
  - **Draft:** Still being prepared.
  - **Active:** Ready for active catalogue use.
  - **Inactive:** Temporarily not active.
  - **Archived:** Kept as a historical record.

A Development cannot be archived while published listings depend on it. Archive those listings first. Archiving a Development does not automatically archive its Variants or Properties. Restoring it returns it to Draft so it can be reviewed before activation.

### House models

A House model (internally called a Variant) is a repeatable design within a Development—for example, “Amara 3-bedroom model.”

- Select the correct **Development** and **Property type**.
- Add the model name, slug, description, and relevant specifications.
- Only make a Variant Active when its Development is also Active.
- Use memorial capacity for memorial products instead of house-specific fields.

### Properties

A Property is one specific unit or piece of inventory.

- **Reference code:** A unique internal identifier, such as `VH-AMARA-001`.
- **Property type:** Must match the selected Variant, if there is one.
- **Development and Variant:** Optional for a standalone property; otherwise they must agree with each other.
- **Location:** Select the correct saved Location.
- **Title override:** Optional customer-friendly name.
- **Unit/Lot number:** Private internal detail; it is not displayed to customers.
- **Specifications:** Bedrooms, bathrooms, parking, floor area, lot area, furnishing, and occupancy.
- **Inventory status:** Available, Reserved, Under Offer, Sold, Rented, or Unavailable.

Use inventory status to reflect the real-world unit. Do not delete a sold or rented property; keep the record and update its status.

### Catalogue media

Catalogue Media connects an uploaded image to exactly one Development, Variant, or Property.

- First upload the photograph or floor plan through **Images** if necessary.
- Choose **Property photo** for normal gallery images or **Floor plan** for a plan image.
- Attach it to exactly one catalogue record.
- Write useful **alt text** describing what is visibly present in the image.
- Add an optional caption.
- Only a **Property photo** can be marked as the cover. Floor plans appear in their own section.
- Use **sort order** to control sequence; lower numbers come first.
- Select **is cover** for the primary image. Only one active cover is allowed per record, and choosing a new cover replaces the old cover selection.

### Listings

A Listing is the public advertisement that customers browse.

- **Title and slug:** Public title and URL identifier.
- **Summary and description:** Preview and full customer-facing copy.
- **Inventory mode:**
  - **Single property:** Choose one Property. Leave Variant and available quantity empty.
  - **Pooled variant inventory:** Choose one Variant and enter how many units are available. Leave Property empty.
- **Public status:** Available, Reserved, Sold, Rented, or Unavailable.
- **Featured:** Highlights the listing in supported areas of the website.
- **SEO title and description:** Optional wording for search engines.

New Listings always begin as Draft. A Listing requires one active Offer and a safe public Location before it can be published.

### Price and availability

A Price and availability record (internally called an Offer) gives a Listing its sale or rental terms. The guided listing form normally manages it automatically. Only one may be active for a Listing at a time.

- **Listing:** The advertisement this pricing belongs to.
- **Transaction type:** For Sale or For Rent.
- **Currency:** Normally `PHP`.
- **Price display:** Exact price, Starting At, Range, Negotiable, or Contact for Price.
- **Price minimum/maximum:** Use values appropriate to the selected display. The maximum cannot be lower than the minimum.
- **Rent period:** Daily, weekly, monthly, or yearly for rental offers.
- **Deposit, minimum lease, reservation fee, and available date:** Complete only when applicable.
- **Active:** The current offer shown with the Listing.

When replacing pricing, deactivate the old Offer before activating another one. This keeps the price history without creating two active offers.

### Inquiries

Inquiries are created when a visitor submits the contact form or asks about a specific Listing.

- **New:** Not handled yet.
- **Contacted:** Lala or an Admin has replied.
- **Qualified:** The customer's needs and ability to proceed have been confirmed.
- **Viewing arranged:** A viewing has been scheduled.
- **Closed—successful:** The inquiry produced a completed result.
- **Closed—not proceeding:** The customer is no longer proceeding.
- **Spam:** Unwanted submission.
- **Archived:** Retained for records but removed from normal active work.

Assign an inquiry only to an active Owner or Admin. Never replace the customer's original message with staff notes.

Customer phone numbers are masked for Admins unless the Owner grants temporary access. Access is logged.

### Inquiry notes

Use Inquiry Notes to record internal follow-up history.

- Select the Inquiry.
- Choose Internal Note, Call, Email, Message, or Viewing.
- Write an objective summary of what happened.
- Set the occurrence date and time accurately.

The system records the signed-in staff member as the author automatically. Do not place passwords, payment-card details, identification documents, or unnecessary sensitive information in notes.

### Article categories

Categories organize Resources articles, such as Homebuyer Guides or Property Tips.

- Use a clear name and matching slug.
- Add an optional description.
- Set **Active** off to hide the category from normal filtering without deleting its articles.
- Use sort order to arrange categories.

### Contact page settings

This single record stores Lala Land's real Facebook, Instagram, TikTok, Messenger, and WhatsApp links. Leave an unsupported service blank. Test every URL after changing it.

The private **Inquiry notification email** receives one alert whenever a customer submits a new inquiry. The alert links directly to the protected CMS record and does not include the customer's phone number. Leave this field blank to disable alerts. Delivery successes and failures appear in the Audit log; a mail failure never discards the customer's saved inquiry.

## 4. Listings review and publishing

The **Listings** menu is the safe place to add, edit, publish, archive, and restore listings.

### Publishing

Before selecting **Publish**, confirm:

- The Listing targets exactly one Property or Variant.
- Its inventory mode matches that target.
- A single active Offer exists.
- The Location has a safe public label and is not Hidden.
- The Development and Variant are Active when applicable.
- The property is Available or Reserved.
- Summary and description are complete.
- Photographs and alt text have been checked.

### Archiving and restoring

- **Archive** removes a Listing from normal public browsing but retains the record and saved URL behavior.
- A visitor opening an archived saved link sees the unavailable page.
- **Restore as draft** returns it to Draft. Review it and publish it manually when ready.
- Restoration never republishes a Listing automatically.

## 5. Inquiry dashboard

Use the **Inquiry dashboard** for daily lead follow-up.

1. Open new inquiries first.
2. Review the customer's request and listing reference.
3. Assign the inquiry to Lala or the responsible Admin.
4. Add a note after every call, message, email, or viewing.
5. Move the status forward as work progresses.
6. Close or archive inquiries only when appropriate.

## 6. Pages and Resources articles

The **Pages** menu controls editorial website pages.

### About page

Edit the introduction, portrait, story, philosophy, approach, community section, and affiliation. If a portrait is selected, meaningful portrait alt text is required.

Use **Save draft** while editing and **Publish** only after previewing the changes.

### Resources page

The Resources page is the parent for all articles. Its introduction can be edited from Pages.

### Creating an article

1. Open **Pages** and select the Resources page.
2. Choose **Add child page**, then Article Page.
3. Enter the title, summary, category, body, and author.
4. Add an optional cover image and required alt text.
5. Select Featured only for articles that should receive extra emphasis.
6. Preview the article.
7. Save a draft or publish it.

Select **Archived** to hide an article while retaining its CMS record. Do not delete useful historical content unless there is a strong reason.

## 7. Images and Documents

### Images

- Upload clear, properly licensed images.
- Use descriptive titles and alt text.
- Avoid uploading several identical copies.
- Do not delete an image while a page or catalogue record still uses it.

### Documents

Documents are for downloadable files linked from articles. Upload only safe, current, publicly shareable files. Do not upload contracts, customer IDs, private spreadsheets, or internal records to the public document library.

## 8. Sensitive-access requests

Admins may request temporary access to either a particular exact Location or customer phone numbers.

### Admin procedure

1. Open the access-request area.
2. Choose the required scope.
3. For an exact location, select the specific Location.
4. Give a clear business reason and reasonable duration.
5. Wait for Owner approval.

### Owner procedure

1. Review who requested access, why, and for how long.
2. Approve only the minimum access actually required, or deny it with a note.
3. Revoke an active grant when it is no longer needed.

Approvals, access, denial, and revocation are recorded for accountability.

## 9. Staff management — Owner only

Use **Staff management** rather than sharing an existing login.

- Invite a staff member as Admin or Maintainer using their own email.
- Invitation links expire and can be used only once.
- Revoke an invitation if it was sent incorrectly.
- Suspend an account for a temporary security or employment issue.
- Disable access when it should end permanently.
- Change Admin/Maintainer roles only when responsibilities change.

Changing a role or account status invalidates that person's active sessions. The Owner role cannot be transferred through ordinary staff management.

## 10. Audit log — Owner only

The **Audit log** records important actions such as catalogue edits, publishing, inquiry work, sensitive access, and staff changes.

Use it when checking who changed something or investigating an unexpected result. Audit records are append-only: staff cannot edit or delete their history.

## 11. Common problems

### “A published listing needs one active offer”

Create or activate one Offer for the Listing, then publish again.

### Inventory-mode or target error

- Single property: select Property only and leave quantity empty.
- Pooled inventory: select Variant only and enter available quantity.

### Location prevents publication

Add a public label and choose Area Only, Exact, or Approximate. Exact and Approximate require a public map pin.

### Development cannot be archived

Open Listing Workflow and archive every published Listing named in the error. Then archive the Development.

### Image cannot be used as a cover

Make sure the media record is active and attached to exactly one catalogue record.

### An article image produces an error

Add alt text that describes the visible content of the selected image.

## 12. Recommended daily and monthly routine

### Daily

- Check new inquiries.
- Record follow-ups and update inquiry status.
- Update sold, rented, reserved, and unavailable inventory promptly.
- Confirm public listings still show accurate pricing and availability.

### Monthly

- Review active Listings and Offers.
- Archive obsolete drafts and inactive content without deleting useful records.
- Review staff access and sensitive-access grants.
- Check the audit log for unusual changes.
- Test the contact form and social links.
- Confirm backups and software maintenance with the technical Maintainer.

## 13. Before launch

- Replace placeholder social links with Lala Land's real accounts.
- Add Lala's professionally reviewed privacy notice and legal content.
- Use production hosting, HTTPS, PostgreSQL backups, and secure environment settings.
- Replace the temporary inquiry notification recipient (`dynzues@gmail.com`) with the approved live business inbox before launch, then verify delivery through the production SMTP provider.
- Test Owner and Admin accounts independently.
- Keep recovery codes secure and separate from the website server.
