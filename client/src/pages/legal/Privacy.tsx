import LegalPage, { ContactDetails, Section, operatorName } from './LegalPage';

const Privacy = () => (
    <LegalPage title="Privacy Policy">
        {site => {
            const us = operatorName(site);
            return (
                <div className="space-y-10">
                    <p className="text-gray-300 leading-relaxed">
                        {site?.app_name ?? 'This platform'} connects customers with local restaurants and their drivers. It is run by {us} ("we").
                        This policy explains what personal information we collect, why, who we share it with, and the rights you have under the
                        Protection of Personal Information Act, 2013 (POPIA).
                    </p>

                    <Section title="1. What we collect">
                        <ul className="list-disc pl-6 space-y-2">
                            <li><strong className="text-white">Account details:</strong> your name, surname, email address, cell number and password (stored only in a scrambled, one-way form).</li>
                            <li><strong className="text-white">Delivery addresses</strong> you save, including the map position you choose.</li>
                            <li><strong className="text-white">Orders:</strong> what you ordered, from which restaurant, the amounts, how you chose to pay, and any rating or comment you leave.</li>
                            <li><strong className="text-white">Drivers' location:</strong> if you deliver for a restaurant, your phone's position while you are online or on a delivery.</li>
                            <li><strong className="text-white">Restaurants:</strong> business details, menu, logo, payment settings and subscription history.</li>
                            <li><strong className="text-white">Technical information</strong> needed to keep the service safe, such as the device and network address used to sign in.</li>
                        </ul>
                        <p>We do not collect or store card numbers. Online payments are entered directly on the secure page of the payment company the restaurant uses (PayFast, Ozow or Peach Payments).</p>
                    </Section>

                    <Section title="2. Why we use it">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>To create your account, take and deliver your orders, and show you their progress.</li>
                            <li>To send messages about your orders, account and (for restaurants) subscription, by SMS, email and in the app.</li>
                            <li>To match orders with the nearest available driver and show customers where their delivery is.</li>
                            <li>To prevent fraud and misuse, and to meet our legal obligations.</li>
                        </ul>
                        <p>We do not sell your personal information and we do not use it for third-party advertising.</p>
                    </Section>

                    <Section title="3. Who sees your information">
                        <ul className="list-disc pl-6 space-y-2">
                            <li><strong className="text-white">The restaurant you order from and its driver</strong> see your name, cell number and delivery address for that order, so they can make and deliver it.</li>
                            <li><strong className="text-white">Customers</strong> see the name, cell number, vehicle and (while delivering) live location of the driver bringing their order.</li>
                            <li><strong className="text-white">Service providers</strong> who process information for us: PayFast, Ozow and Peach Payments (online payments), Africa's Talking (SMS), Resend (email) and our hosting and database providers. Some of them may store information outside South Africa; we only use providers that protect it to a standard comparable to POPIA.</li>
                            <li><strong className="text-white">Authorities</strong>, when the law requires it.</li>
                        </ul>
                        <p>Restaurants cannot see other restaurants' orders or customers.</p>
                    </Section>

                    <Section title="4. How long we keep it">
                        <p>
                            We keep your account while you use it. Order and payment records are kept for as long as tax and accounting law requires
                            (usually five years). In-app notifications are deleted after 30 days, and a driver's live position is only kept for a few minutes.
                        </p>
                    </Section>

                    <Section title="5. Keeping it safe">
                        <p>
                            Passwords are scrambled before they are stored, restaurants' payment keys are encrypted, and connections to the service are encrypted.
                            No system is perfectly secure; if a breach affects you, we will tell you and the Information Regulator as POPIA requires.
                        </p>
                    </Section>

                    <Section title="6. Your rights">
                        <p>You may ask us to:</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>tell you what personal information we hold about you and give you a copy;</li>
                            <li>correct it (you can change your name, cell number and email yourself under your account settings);</li>
                            <li>delete it, unless we must keep it by law;</li>
                            <li>stop using it for a particular purpose, or stop sending you non-essential messages.</li>
                        </ul>
                        <p>
                            If you are unhappy with how we handle your information, you may complain to the Information Regulator (South Africa),
                            at <a href="https://inforegulator.org.za" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:text-brand-400">inforegulator.org.za</a>.
                        </p>
                    </Section>

                    <Section title="7. Storage on your device">
                        <p>
                            The app stores your sign-in session and your cart on your device so they survive a page refresh. We do not use advertising or tracking cookies.
                        </p>
                    </Section>

                    <Section title="8. Changes">
                        <p>If we change this policy we will update the date at the top, and tell you in the app if the change is significant.</p>
                    </Section>

                    <Section title="9. Contact us">
                        <ContactDetails site={site} />
                    </Section>
                </div>
            );
        }}
    </LegalPage>
);

export default Privacy;
